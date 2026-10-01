"""Check actual packed glyphs, CRCs, and preservation of the original resources."""
import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = "₽€₪₴₸₾֏£¥¢₹₩₺₿№°±×÷−‰…«»“”‘’–—•·\u00a0\u202f\u2009"


def read_pack(path, builder):
    sys.path.insert(0, str(builder))
    from utils.pbpack import ResourcePack
    from utils.stm32_crc import crc32
    data = Path(path).read_bytes()
    assert crc32(data[ResourcePack.CONTENT_START_OFFSET:]) == struct.unpack_from('<I', data, 4)[0], 'Pack CRC mismatch'
    with Path(path).open('rb') as stream:
        pack = ResourcePack.deserialize(stream)  # also checks every resource CRC
    assert len(pack.contents) == 19, 'Expected original metadata + 18 font variants'
    return pack.contents


def glyphs(data):
    version, height, count, fallback, buckets, cp_bytes = struct.unpack_from('<BBHHBB', data)
    assert version == 2 and cp_bytes == 2
    offset_start = 8 + buckets * 4
    bitmap_start = offset_start + count * 6
    result = {}
    for bucket in range(buckets):
        index, size, offset = struct.unpack_from('<BBH', data, 8 + bucket * 4)
        assert index == bucket
        for entry in range(size):
            cp, glyph_offset = struct.unpack_from('<HI', data, offset_start + offset + entry * 6)
            start = bitmap_start + glyph_offset
            width, rows = struct.unpack_from('<BB', data, start)
            end = start + 5 + ((width * rows + 31) // 32) * 4
            assert end <= len(data), 'Truncated glyph'
            assert cp not in result, 'Duplicate codepoint'
            result[cp] = data[start:end]
    assert len(result) == count and fallback in result
    return height, result


def verify(path, builder, baseline):
    resources = read_pack(path, builder)
    original = read_pack(baseline, builder)
    assert resources[0] == original[0], 'Language metadata changed'
    for variant in range(1, 19):
        height, actual = glyphs(resources[variant])
        old_height, old = glyphs(original[variant])
        assert height == old_height, f'{variant:03}: font height changed'
        for cp, bitmap in old.items():
            assert actual.get(cp) == bitmap, f'{variant:03}: original U+{cp:04X} changed'
        for char in SYMBOLS:
            cp = ord(char)
            assert cp in actual, f'{variant:03}: missing {char!r} U+{cp:04X}'
            assert actual[cp] != actual[0x25AF], f'{variant:03}: fallback bitmap for U+{cp:04X}'
            if not char.isspace():
                assert any(actual[cp][5:]), f'{variant:03}: blank glyph U+{cp:04X}'
            else:
                assert struct.unpack_from('<b', actual[cp], 4)[0] > 0, 'Space has no advance'
    print(f'PASS: CRCs, {len(SYMBOLS)} symbols in all 18 variants, and every original glyph unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pack', type=Path)
    parser.add_argument('--builder', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'pebble-EN-RU-HE.pbl')
    args = parser.parse_args()
    verify(args.pack, args.builder.resolve(), args.baseline)
