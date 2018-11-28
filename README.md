a C port of the [coco/r](http://www.ssw.uni-linz.ac.at/Coco/) parser generator.

v1.17 by Frankie Arzu corrected by me (realloc sometimes broke program memory. the algo has been slightly modified)

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
  - =>  (_C_)  if( `..cond..` ){ `..a..` }else{ `..b..` }
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
