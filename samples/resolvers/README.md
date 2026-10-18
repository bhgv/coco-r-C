# C resolver example / Пример условий IF

[choices.atg](choices.atg) demonstrates guarded alternatives, an optional part,
a bounded repetition and an exact UTF-8 literal. Every source line is commented.
The generated code is C and does not require a C++ runtime.

From the repository root, using a POSIX shell and a C compiler:

```sh
make -C sources -f unix.mk
cd samples/resolvers
CRFRAMES=../../frames ../../cocor choices.atg
cc -o choices choice.c choicep.c choices.c
./choices input.txt
```

Expected output:

```text
guarded branch
z count: 2
```

The first alternative uses a resolver even though both alternatives start with
`x`. Change `count == 0` to `count != 0` to exercise the fallback. The option
uses `Sym` to inspect lookahead. The loop tests both lookahead and a counter;
it consumes input and changes the counter on each iteration. It stops before a
third `z`, which would then produce a syntax error at the expected `中文` token.
The generator does not prove termination or type-check C expressions.

| Construct/API | Purpose | Documentation |
| --- | --- | --- |
| `IF(expression)` | Override prediction at a branch, option or loop | [Resolver semantics](../../docs/RESOLVERS_UTF8.md#if-resolvers) |
| `Sym`, generated `xSym`, `ySym`, `zSym` | Inspect the current lookahead token without consuming it | [Lookahead and consumption](../../docs/RESOLVERS_UTF8.md#lookahead-and-consumption) |
| `(. ... .)` | Execute C code after matching input | [Implementation and source links](../../docs/RESOLVERS_UTF8.md#implementation-and-source-links) |
| UTF-8 `"中文"` | Match the exact encoded bytes | [UTF-8 contract](../../docs/RESOLVERS_UTF8.md#utf-8-contract) |

По-русски: IF выбирает ветвь, но сам не читает токен. В `[]` условие проверяется
один раз, в `{}` — перед каждой итерацией. Если условие ложно, вход остаётся
нетронутым. Незащищённая условием ветвь после `|` по-прежнему проверяет FIRST/FOLLOW,
поэтому её нельзя считать безусловным C `else`. Подробности и ограничения
описаны в [руководстве](../../docs/RESOLVERS_UTF8.md).
