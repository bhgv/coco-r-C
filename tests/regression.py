#!/usr/bin/env python3
"""Compile and run generated C parsers in isolated temporary directories."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, CRFRAMES=str(ROOT / 'frames'))
CC = os.environ.get('CC', 'cc')
FLAGS = os.environ.get('TEST_CFLAGS', '-O0 -g').split()


def run(args, cwd, ok=True):
    result = subprocess.run([str(a) for a in args], cwd=cwd, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if b'runtime error:' in result.stderr or b'ERROR: AddressSanitizer' in result.stderr:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    if ok and result.returncode:
        raise RuntimeError(f'{args}\n{result.stdout!r}\n{result.stderr!r}')
    return result


def grammar(directory, body, declarations='', header='', bom=False):
    text = ('$C\nCOMPILER Demo\n#include <stdio.h>\n' + header + '\n' +
            declarations + '\nPRODUCTIONS\nDemo = ' + body + '\nEND Demo.\n')
    (directory / 'demo.atg').write_text(('\ufeff' if bom else '') + text, encoding='utf-8')
    return run([ROOT / 'cocor', 'demo.atg'], directory, ok=False)


def case(body, data, expected, declarations='', header='', bom=False, valid=True):
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        result = grammar(directory, body, declarations, header, bom)
        if result.returncode:
            raise RuntimeError(result.stderr.decode())
        run([CC, *FLAGS, '-o', 'demo', 'demo.c', 'demop.c', 'demos.c'], directory)
        (directory / 'input').write_text(data, encoding='utf-8')
        result = run([directory / 'demo', 'input'], directory, ok=False)
        if (result.returncode == 0) != valid or result.stdout.decode().strip() != expected:
            raise RuntimeError(f'{data!r}: {result.returncode}, {result.stdout!r}, {result.stderr!r}')


def errno_macro_case():
    """Generated headers and definitions must tolerate an existing errno macro."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        result = grammar(directory, '"x" (. if (errno != 17) abort(); puts("ok"); .) .')
        if result.returncode:
            raise RuntimeError(result.stderr.decode())
        # Model the pointer-valued errno macro exposed by Windows stdlib.h,
        # while also including the native libc's real errno header first.
        prefix = ('#include <stdio.h>\n#include <stdlib.h>\n#include <errno.h>\n'
                  'static int test_errno_value = 17;\n'
                  'static int *cocor_test_errno(void) { return &test_errno_value; }\n'
                  '#undef errno\n#define errno (*cocor_test_errno())\n')
        (directory/'probe.c').write_text(prefix + '#include "demop.h"\n'
            'void probe(void) { SynError(1000); SemError(1001); }\n')
        run([CC, *FLAGS, '-Werror', '-c', 'probe.c', '-o', 'probe.o'], directory)
        (directory/'embedded.c').write_text(prefix + '#include "demop.c"\n')
        run([CC, *FLAGS, '-o', 'demo', 'demo.c', 'embedded.c', 'demos.c'], directory)
        (directory/'input').write_text('x')
        result = run([directory/'demo', 'input'], directory)
        if result.stdout.strip() != b'ok':
            raise RuntimeError('errno macro value changed during parsing')
        (directory/'input').write_text('y')
        if run([directory/'demo', 'input'], directory, ok=False).returncode == 0:
            raise RuntimeError('parser error reporting stopped rejecting invalid input')


def main():
    run(['make', '-C', 'sources', '-f', 'unix.mk'] +
        (['CFLAGS=' + ' '.join(FLAGS)] if 'TEST_CFLAGS' in os.environ else []), ROOT)
    errno_macro_case()
    # A rejected guarded branch must leave the same-token fallback available.
    for choice in (0, 1):
        case('( IF(choose && (1)) "x" (. puts("yes"); .) | '
             '"x" (. puts("no"); .) ) .', 'x', 'yes' if choice else 'no',
             header=f'static int choose = {choice};')
    # Predicates replace prediction, so they cannot justify skipping Expect().
    case('( IF(1) "x" | "y" ) .', 'y', '', valid=False)
    case('( IF((")"[0] == 41) /* ) */ && (1)) "x" '
         '(. puts("nested"); .) | "y" ) .', 'x', 'nested')
    case('( IF(((int[]){1, 2})[0] == 1) "x" (. puts("braces"); .) | "y" ) .',
         'x', 'braces')
    case('[ IF(0) "x" ] "x" (. puts("optional"); .) .', 'x', 'optional')
    case('{ IF(Sym == xSym && count < 2) "x" (. ++count; .) } '
         '"x" (. printf("%d\\n", count); .) .', 'xxx', '2', header='static int count;')
    case('( [ IF(0) "x" ] | "y" ) "x" (. puts("kept"); .) .', 'x', 'kept')
    # Exact UTF-8 literals, shared prefixes and BOM in grammar and input.
    for word in ('привет', 'приз', '中文', '😀'):
        case('( "привет" | "приз" | "中文" | "😀" ) (. puts("utf8"); .) .',
             '\ufeff' + word, 'utf8', bom=True)
    for word in ('приветик', 'приветствие'):
        case('( "приветик" (. puts("one"); .) | "приветствие" (. puts("two"); .) ) .',
             word, 'one' if word == 'приветик' else 'two')
    # A keyword recognized through CheckLiteral, rather than a literal-only DFA.
    case('"привет" (. puts("keyword"); .) .', 'привет', 'keyword',
         declarations='CHARACTERS\nhi = CHR(128) .. CHR(255).\nTOKENS\nword = hi { hi }.')
    case('word (. char value[40]; LexString(value, 39); puts(value); .) .', '中文', '中文',
         declarations='CHARACTERS\nhi = "中文".\nTOKENS\nword = hi { hi }.')
    case('"привет" "abc" (. puts("case"); .) .', 'приветABC', 'case',
         declarations='IGNORE CASE')
    case('"x" (. /*' + 'a' * 2000 + '*/\tputs("long"); .) .', 'x', 'long')
    for body in ('( IF() "x" | "y" ) .', '( IF(/* empty */) "x" | "y" ) .', '( IF((1) "x" | "y" ) .',
                 '"x" IF(1) "y" .', 'IF(1) "x" .', '"' + 'я' * 25 + '" .'):
        with tempfile.TemporaryDirectory() as tmp:
            if grammar(Path(tmp), body).returncode == 0:
                raise RuntimeError('Accepted invalid grammar: ' + body)
    # The documented example uses Coco/R's historical six-character module prefix.
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for name in ('choices.atg', 'input.txt'):
            (directory / name).write_bytes((ROOT / 'samples' / 'resolvers' / name).read_bytes())
        run([ROOT / 'cocor', 'choices.atg'], directory)
        run([CC, *FLAGS, '-o', 'choices', 'choice.c', 'choicep.c', 'choices.c'], directory)
        result = run([directory / 'choices', 'input.txt'], directory)
        if result.stdout.decode().strip() != 'guarded branch\nz count: 2':
            raise RuntimeError('Example output changed')
    # Existing sample outcomes: three grammars were already invalid on the baseline.
    invalid_samples = {'c.atg', 'pascal.atg', 'umbriel1.atg'}
    for source in sorted((ROOT / 'samples').glob('*.atg')):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / source.name).write_bytes(source.read_bytes())
            result = run([ROOT / 'cocor', source.name], directory, ok=False)
            if (result.returncode != 0) != (source.name in invalid_samples):
                raise RuntimeError('Unexpected sample outcome: ' + source.name)
    # Checked-in generated sources and a second-generation executable agree.
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for name in ('cr.atg', 'cr.frm'):
            (directory / name).write_bytes((ROOT / 'sources' / name).read_bytes())
        run([ROOT / 'cocor', 'cr.atg'], directory)
        names = ('cr.c', 'crc.h', 'cre.h', 'crp.c', 'crp.h', 'crs.c', 'crs.h')
        first = {name: (directory / name).read_bytes() for name in names}
        for name in names:
            if first[name] != (ROOT / 'sources' / name).read_bytes():
                raise RuntimeError('Stale generated source: ' + name)
        run([CC, *FLAGS, '-I', ROOT / 'sources', '-o', 'stage2',
             *[directory / name for name in ('cr.c', 'crp.c', 'crs.c')],
             *[ROOT / 'sources' / (name + '.c') for name in
               ('cra', 'crt', 'crx', 'crf', 'collect', 'set')]], directory)
        run([directory / 'stage2', 'cr.atg'], directory)
        if any(first[name] != (directory / name).read_bytes() for name in names):
            raise RuntimeError('Self-hosting did not reach a fixed point')
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        if grammar(directory, '"中文" .').returncode:
            raise RuntimeError('Buffer grammar failed')
        (directory / 'buffer.c').write_text('''#include "demos.h"
#include <string.h>
int main(void) {
    unsigned char text[] = {0xe4,0xb8,0xad,0xe6,0x96,0x87};
    char value[7];
    int i;
    for (i = 0; i < 50; ++i) {
        S_Reset(text, sizeof(text));
        if (S_Get() == No_Sym || S_NextLen != 6) return 1;
        S_GetString(S_NextPos, S_NextLen, value, 6);
        if (memcmp(text, value, 6)) return 2;
        if (S_CurrentCh(-1) || S_CurrentCh(7)) return 3;
        if (S_Get() != EOF_Sym || S_Get() != EOF_Sym) return 4;
    }
    S_Reset(0, 0);
    return S_Get() != EOF_Sym;
}
''')
        run([CC, *FLAGS, '-DCUSTOM_BUFF', '-o', 'buffer', 'buffer.c', 'demos.c'], directory)
        run([directory / 'buffer'], directory)
        run([CC, *FLAGS, '-I', ROOT / 'sources', '-o', 'collection',
             ROOT / 'tests' / 'collection.c', ROOT / 'sources' / 'collect.c'], directory)
        run([directory / 'collection'], directory)
    print('All resolver, UTF-8 byte-scanner, buffer, collection and self-host tests passed.')


if __name__ == '__main__':
    main()
