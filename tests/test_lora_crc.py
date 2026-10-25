"""Offline checks of actual CRC member bodies, without constructing a modem.

The small host supplies only their scalar/array fields. No packet encoder,
modulator, device, radio output, or application transmit loop is linked.
"""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "fldigi-noise-sdr/src/fldigi/lora/lora.cxx"


def member(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


HOST = r"""
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
class lora {
public:
    bool has_crc = true;
    int payload_cnt = 0;
    int len = 5;
    unsigned int payload[255] = {};
    int data[519] = {};
    unsigned int crc16(unsigned int, unsigned char);
    void add_crc();
};
__MEMBERS__

// Independent polynomial long division of the unaugmented payload bits.
static unsigned remainder(const unsigned int* bytes, int count) {
    unsigned value = 0;
    for (int i = 0; i < count; ++i)
        for (int bit = 7; bit >= 0; --bit) {
            value = (value << 1) | ((bytes[i] >> bit) & 1);
            if (value & 0x10000) value ^= 0x11021;
        }
    return value;
}
static void check(lora& sample) {
    std::fill(std::begin(sample.data), std::end(sample.data), -7);
    sample.len = 5;
    sample.add_crc();
    assert(sample.len == 9);
    unsigned actual = 0;
    for (int j = 0; j < 4; ++j) {
        assert(sample.data[5 + j] >= 0 && sample.data[5 + j] <= 15);
        actual |= unsigned(sample.data[5 + j]) << (j * 4);
    }
    assert(actual == remainder(sample.payload, sample.payload_cnt));
    for (int j = 0; j < 5; ++j) assert(sample.data[j] == -7);
    for (int j = 9; j < 519; ++j) assert(sample.data[j] == -7);
    sample.has_crc = false;
    sample.len = 5;
    std::fill(std::begin(sample.data), std::end(sample.data), -7);
    sample.add_crc();
    assert(sample.len == 5);
    for (int j = 0; j < 519; ++j) assert(sample.data[j] == -7);
    sample.has_crc = true;
}
int main(int argc, char** argv) {
    lora sample;
    if (argc > 1) {
        sample.payload_cnt = std::atoi(argv[1]);
        sample.payload[0] = 0x42;
        check(sample);
        return 0;
    }
    unsigned cases = 0;
    sample.payload_cnt = 0;
    check(sample); ++cases;
    sample.payload_cnt = 1;
    for (unsigned a = 0; a < 256; ++a) {
        sample.payload[0] = a; check(sample); ++cases;
    }
    sample.payload_cnt = 2;
    for (unsigned a = 0; a < 256; ++a)
        for (unsigned b = 0; b < 256; ++b) {
            sample.payload[0] = a; sample.payload[1] = b;
            check(sample); ++cases;
        }
    for (int count = 3; count <= 255; ++count)
        for (unsigned pattern = 0; pattern < 4; ++pattern) {
            sample.payload_cnt = count;
            for (int i = 0; i < count; ++i)
                sample.payload[i] = pattern == 0 ? 0 : pattern == 1 ? 255
                    : (unsigned(i) * 73 + unsigned(count) * 19 + pattern * 41) & 255;
            check(sample); ++cases;
        }
    std::cout << "checksum cases=" << cases << "; CRC-disabled preservation included\n";
}
"""


class LoraChecksumTests(unittest.TestCase):
    def test_actual_crc_members_with_bounds_checks(self):
        compiler = shutil.which("c++")
        if compiler is None:
            self.skipTest("A C++ compiler is required for the offline checksum fixture")
        source = SOURCE.read_text()
        functions = "\n".join(member(source, signature) for signature in (
            "unsigned int lora::crc16(", "void lora::add_crc()"))
        self.assertEqual(len(re.findall(r"lora::(?:crc16|add_crc)\(", functions)), 2)
        with tempfile.TemporaryDirectory(prefix="signalforge-crc-") as directory:
            path = Path(directory)
            unit = path / "crc.cxx"
            binary = path / "crc"
            unit.write_text(HOST.replace("__MEMBERS__", functions))
            subprocess.run([compiler, "-std=c++11", "-O1", "-g", "-fsanitize=undefined",
                            "-fno-sanitize-recover=all", str(unit), "-o", str(binary)],
                           check=True, capture_output=True, text=True, timeout=60)
            result = subprocess.run([str(binary)], check=True, capture_output=True,
                                    text=True, timeout=30)
            self.assertIn("checksum cases=66805", result.stdout)


if __name__ == "__main__":
    unittest.main()
