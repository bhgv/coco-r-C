# C resolvers and UTF-8 byte strings

## Build and test

```sh
make -C sources -f unix.mk
python3 tests/regression.py
```

Generation requires only C. Python 3 is used by the regression runner, not by
Coco/R or its generated programs. Generated parsers must be regenerated with
the updated C frames to receive scanner fixes.

## IF resolvers

A resolver is `IF(C-expression)` at the beginning of an alternative, option or
repetition. It is zero-width: it evaluates a condition without consuming input.

```text
( IF(condition) A | B )
[ IF(condition) A ]
{ IF(condition) A }
```

The first form emits `if (condition)` for A. B retains its normal lookahead
prediction: it is generally `else if (FIRST/FOLLOW-test)`, not an unconditional
`else`. Further alternatives can have their own leading resolvers. `[]` emits
`if`; `{}` emits `while`, with the condition reevaluated at every iteration.
Ordinary parentheses group grammar expressions, square brackets make them
optional, and braces repeat them; IF does not change these meanings.

The condition replaces, rather than supplements, the normal token test.
Include the lookahead test in the condition when it is needed. Expressions
may contain nested parentheses, character/string literals and comments. Their
original source bytes are copied into C. Coco/R checks delimiter balance and
placement; the C compiler checks the expression's syntax, names and types.
Empty conditions and IF after a consumed symbol or semantic action are errors.
Standalone `Rule = IF(condition) A .` is rejected: there is no decision there.
Use `[ IF(condition) A ]` for a conditional optional part.

Resolvers resolve a particular prediction conflict. FIRST/FOLLOW sets still
exist, and ordinary unguarded ambiguity diagnostics remain. An unguarded
alternative appearing before a guarded one can shadow it: order matters.
Avoid side effects in predicates unless repeated evaluations are intentional.
A repetition must consume input or change state so its predicate eventually
becomes false; the generator cannot guarantee termination.

### Lookahead and consumption

`Sym` in generated parser code is the current lookahead token kind. The token
constants are emitted into the generated `*c.h` header. `IF` does not call
`Get()`. Terminals in a guarded branch still call `Expect()` when no actual
token test has established their kind. A true predicate with the wrong token
therefore reports a syntax error instead of accepting arbitrary input.

See the commented [example and build instructions](../samples/resolvers/README.md).

## UTF-8 contract

This implementation remains an **8-bit, byte-oriented scanner**, with a
256-entry transition table. It preserves and matches UTF-8 byte sequences;
it does not decode Unicode scalar values.

Supported and regression-tested:

- Exact Russian and Chinese literals, emoji and literals with shared prefixes.
- UTF-8 keywords recognized inside a broader token through `CheckLiteral`.
- Exact `S_GetString`/`LexString` retrieval of token bytes.
- UTF-8 BOM at the start of a grammar or generated scanner input.
- Unsigned high bytes in character sets, with either signed or unsigned C `char`.
- ASCII `IGNORE CASE` without modifying UTF-8 high bytes.

Important limits:

- `CHR(0)..CHR(255)` and `CHARACTERS` describe **bytes**. `"中文"` in a
  production matches the complete sequence; in `CHARACTERS` it is a set of
  individual encoded bytes, not a set of two Unicode characters. A token made
  from arbitrary high bytes does not validate UTF-8 and can accept malformed
  sequences. A Unicode-aware identifier rule needs explicit UTF-8 byte patterns
  or a separate decoding scanner design.
- Grammar identifiers retain their ASCII definition. There is no Unicode case
  folding, normalization, Unicode-property class or codepoint range support.
- Positions, lengths and columns count bytes (with existing tab expansion),
  not Unicode characters or display cells. BOM occupies three source bytes.
- Symbol table names, including quoted production literals with their quotes,
  retain the historical maximum of 31 bytes. General quoted text such as a
  character-set string has a 99-byte limit. Overlong text now produces error
  E132 instead of silently truncating names or UTF-8 sequences. Use a named
  token assembled from shorter string factors for longer exact sequences.
- NUL remains the scanner's EOF sentinel; embedded NUL input is unsupported.
- Save grammar and input as UTF-8 and compile generated C with a compiler whose
  source/execution character encoding preserves UTF-8 (the tested GCC defaults).

## Scanner buffer ownership

`S_Reset(text, text_len)` with `CUSTOM_BUFF` copies exactly `text_len` bytes into
owned storage and appends EOF there. The caller's buffer may be read-only or
exactly sized; no spare byte is required. The caller can release it after reset.
A later reset replaces the internal copy. `NULL, 0` is accepted as empty input;
negative lengths and `NULL` with a positive length terminate with a diagnostic.
The scanner retains its current owned buffer until the next reset or process
exit. Resetting is not a streaming API and scanner globals are not reentrant.

`S_CurrentCh` returns EOF for out-of-range positions. `S_GetString` and
`S_GetName` stop at input bounds; their `max` argument excludes the trailing
NUL, so callers must provide `max + 1` bytes. A byte-count limit can split a
UTF-8 sequence: callers must choose boundaries themselves. `S_GetName` folds
ASCII only when `IGNORE CASE` is enabled. Repeated EOF reads are safe.

The updated and tested ownership path is the linear buffer used by Unix and
modern Windows builds. The historical segmented MS-DOS path was not tested;
`CUSTOM_BUFF` explicitly requires a linear-buffer build.

## Audit fixes and verification

The original collection grew by copying records and losing the old allocation,
while saved pointers still referred to the old records. Records now have stable
addresses; only their pointer table moves. Growth no longer loses edits through
saved pointers. Invalid negative and one-past-live indexes are rejected, and
callback growth preserves the iteration count present at entry. `Clean` reuses
storage and `New` zeroes reused records; `Done` frees the table and records,
but does not free allocations referenced by fields inside records.

Other fixes cover signed-byte set indexing, non-ASCII literal dispatch,
unique generated names for long escaped UTF-8 literals, keyword escaping buffers, bounded frame indentation, long semantic-code lines,
scanner EOF bounds, repeated reset ownership and incomplete file reads.
This was a targeted audit, not a proof that every historical path is free of bugs.

`tests/regression.py` compiles and executes generated C. It covers branch
fallbacks, wrong-token detection, nested conditions, options/repetitions, invalid
conditions/placement, UTF-8 cases, long semantic lines, buffer ownership and a
two-generation self-hosting fixed point. `tests/collection.c` stresses 10,000
records, callback growth, stable pointers and storage reuse. Thirteen of the
sixteen bundled sample grammars generate successfully. `c.atg`, `pascal.atg`
and `umbriel1.atg` already fail on the baseline and remain explicit expected
failures; their unrelated grammar issues were not changed.

For the sanitizer run on GCC/Linux:

```sh
make -C sources -f unix.mk new CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie -no-pie'
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 TEST_CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie -no-pie' python3 tests/regression.py
```

Leak checking is disabled for this full-process test because the legacy
generator retains nested graph/set allocations until process exit. This run
checks memory accesses and undefined behavior, and is not a leak-free claim.

## Implementation and source links

| Symbol/area | Source |
| --- | --- |
| `Resolver`, `Term`, `CheckSymbol`, quoted text limits | [Authoritative ATG grammar](../sources/cr.atg) |
| `T_RESOLVER`, `GraphNode`, `MAX_ID_LEN`, `MAX_STR_LEN` | [Graph and symbol definitions](../sources/crt.h) |
| `IsNullableNode`, `CheckResolverGraph`, `CompSymbolSets` | [Grammar analysis](../sources/crt.c) |
| `HasResolver`, `GenCondition`, `GenFuncGraph`, `GenSemCode` | [C parser generator](../sources/crx.c) |
| `GenLiterals`, `fixname` | [Scanner generator](../sources/cra.c) |
| `S_Reset`, `S_CurrentCh`, `EqualStr`, `CheckLiteral` | [C scanner frame](../frames/scan_c.frm) |
| Scanner public declarations | [Scanner header frame](../frames/scan_h.frm) |
| `Collection_*`, `Collection` | [Implementation](../sources/collect.c), [header](../sources/collect.h) |
| `Set_AddItem`, `Set_IsItem`, `Set_DelItem` | [Byte/symbol bit sets](../sources/set.c) |
| `CopyNextCh` | [Frame copying](../sources/crf.c) |

## Кратко по-русски

Добавлен IF из модели Coco/R C++: условия в начале альтернатив, опций и
повторений генерируют C `if`/`while`. Условие заменяет предсказание по токену;
последующая ветвь без IF всё ещё проверяется по FIRST/FOLLOW. Условия не читают
вход, а проверка ожидаемых терминалов сохраняется.

Нелатинские строки UTF-8 распознаются побайтово, включая ключевые слова внутри
общего токена. Это не полноценный Unicode-сканер: классы, длины и позиции
остаются байтовыми; нормализации и Unicode-регистра нет. Исторический лимит
имён/литералов — 31 байт вместе с кавычками — теперь проверяется явно, а не
обрезает строку незаметно. Для длинной последовательности используйте именованный
токен из нескольких коротких строковых факторов.
