a C port of the [coco/r](http://www.ssw.uni-linz.ac.at/Coco/) parser generator.

v1.17 by Frankie Arzu corrected by me (realloc sometimes broke program memory. the algo has been slightly modified)

Build and regression tests:

```sh
make -C sources -f unix.mk
python3 tests/regression.py
```

The C backend now supports `IF(C-expression)` resolvers in alternatives,
options and repetitions. See [semantics, UTF-8 support and audit notes](docs/RESOLVERS_UTF8.md)
and the [commented C example](samples/resolvers/README.md).
UTF-8 strings are supported as byte sequences; this is not a Unicode-codepoint scanner.

Generated C parser headers and error functions use `error_number` for diagnostic
parameters, so including `<errno.h>` (or Windows `<stdlib.h>`) before a generated
header does not expand the parameter as an `errno` macro. Function names and
argument types are unchanged. `tests/regression.py` checks header inclusion,
parser definitions, the retained errno value and invalid-input rejection.

a light introduction:
====================

coco/r part:
------------
- words in quotes (`'..'` or `".."`)
  - =>  are tokens (lex, flex)
- Foo = `...` .
  - =>  (_C_) void Foo(){ `...` }
- Foo< `..a..` > = `..b..` .
  - =>  (_C_) void Foo( `..a..` ){ `..b..` }
- ( `...` )
  - =>  (_regexp_)  ( `...` )
- [ `...` ]
  - =>  (_regexp_)  ( `...` )?
- { `...` }
  - =>  (_regexp_)  ( `...` )*
- `..a..` | `..b..`
  - =>  (_C_)  `..a..` || `..b..`  (or if() .. else if .. or switch.)
- `..a..` `..b..`
  - =>  (_C_)  `..a..` && `..b..`
- SYNC
  - =>  synchronization point. if there is some error, then control is passed here. the error may be checked with built-in functions. or don't check, but just continue the parsing.
- ( IF( `..cond..` ) `..a..` | `..b..` )
  - => (_C_) `if (cond) { a } else if (lookahead_for_b) { b }`; the fallback still uses token prediction.
- { IF( `..cond..` ) `...` }
  - =>  (_C_)  while( `..cond..` ){ `...` }
- (. `...` .)
  - =>  an adding on the destination language to make some execution of the just parsed construction, or in the place of appearing

- COMPILER `..Name..`   ....   END `..Name..` .
  - =>  begin and end of parser. also, `..Name..` is a entry to start parsing. `..Name..` should be the first parser function.
- CHARACTERS
  - =>  named sets/groups of characters. (`+` => with, and) (`-` => without)
- TOKENS
  - =>  masks to select tokens that don't have a single value, but have the possibility to be selected by a mask. they are specified using characters and strings in quotes, groups of characters and coco/r-regexps (see above)
- IGNORE
  - =>  symbols and group of symbols to be ignored in time of parsing. (`+` => with) (`-` => without) (space and tab are ignored by default)
- COMMENTS FROM `..a..` TO `..b..`
  - =>  parser will ignore the text between `..a..` and `..b..`
- PRAGMA ... .
  - =>  some mask defined using coco/r-regexp for special or complicated to parse fings. it is scanned as a comment, but may have addings ( `(.` ... `.)` ) to parse/execute by hands
- PRODUCTIONS
  - =>  end of the definition of the scanner and begin of the definition of the parser

C-part:
-------
- `S_Pos`, `S_Len`, `LexString()`, `LexName()`
  - =>  current token: position in the source buffer, length, function to get it, capitalised function to get if `IGNORE CASE` is defined
- `S_NextPos`, `S_NextLen`, `LookAheadString()`, `LookAheadName()`
  - =>  next (look ahead) token: position in the source buffer, length, function to get it, capitalised function to get if `IGNORE CASE` is defined
- `SynError()`
  - =>  report a syntax error
- `SemError()`
  - =>  report a semantic error
- `Successfull()`
  - =>  check if parse passed without errors

this is the main part of the coco/r language syntax and part of the internal C-api.
