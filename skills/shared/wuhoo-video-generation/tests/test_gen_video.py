"""Zero-cost unit tests for gen_video.py — no API calls, no credit spend.

Run: python3.11 -m pytest skills/shared/wuhoo-video-generation/tests/ -v
"""
import base64
import io
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

import gen_video as gv

SCRATCH = Path("/home/admin/.hermes/cache/scratch")


def _decode(url):
    assert url.startswith("data:image/")
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))


class TestCli:
    def test_help_surface(self):
        r = subprocess.run(
            [sys.executable, str(Path(gv.__file__).resolve()), "--help"],
            capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr
        for token in ("--last-frame", "--ref-image", "--ref-audio", "--submit-only",
                      "--task-id", "--no-audio", "--prompt-extend", "wan3.0-video-prime"):
            assert token in r.stdout, f"missing {token}"

    def test_prompt_required(self):
        r = subprocess.run(
            [sys.executable, str(Path(gv.__file__).resolve())],
            capture_output=True, text=True, timeout=30)
        assert r.returncode != 0
        assert "--prompt" in r.stderr


class TestConfig:
    def test_discovery_no_secret_leak(self):
        base, key = gv.get_config()
        assert "token-plan" in base and base.endswith("aliyuncs.com")
        assert "/compatible-mode" not in base and not base.endswith("/v1")
        assert len(key) > 10  # presence only, never printed


class TestImagePrep:
    def test_rgba_white_composite(self, tmp_path):
        p = tmp_path / "rgba.png"
        img = Image.new("RGBA", (512, 768), (200, 30, 30, 128))
        # left half fully transparent; sample far from the color edge
        for x in range(256):
            for y in range(768):
                img.putpixel((x, y), (0, 0, 0, 0))
        img.save(p)
        out = _decode(gv.prepare_image(str(p)))
        assert out.mode == "RGB" and out.size == (512, 768)
        px = out.getpixel((128, 384))
        assert min(px) >= 250, f"transparent region not white: {px}"

    def test_oversize_rescale_reencodes(self, tmp_path):
        p = tmp_path / "big.png"
        Image.new("RGB", (9000, 1200), (10, 20, 30)).save(p)
        out = _decode(gv.prepare_image(str(p)))
        assert max(out.size) <= 8000 and min(out.size) >= 240, out.size
        assert max(out.size) / min(out.size) <= 8, out.size

    def test_aspect_over_8to1_rejected(self, tmp_path):
        p = tmp_path / "wide.png"
        Image.new("RGB", (9000, 1000), (10, 20, 30)).save(p)
        with pytest.raises(ValueError, match="8:1"):
            gv.prepare_image(str(p))

    def test_small_image_upscaled_to_240(self, tmp_path):
        p = tmp_path / "tiny.png"
        Image.new("RGB", (100, 100), (1, 2, 3)).save(p)
        out = _decode(gv.prepare_image(str(p)))
        assert min(out.size) >= 240, out.size


class TestComboPreflight:
    def test_frame_and_reference_mutually_exclusive(self):
        with pytest.raises(ValueError, match="互斥"):
            gv.validate_combo([{"type": "first_frame", "url": "x"},
                               {"type": "reference_image", "url": "y"}])

    def test_file_link_exclusive(self):
        with pytest.raises(ValueError):
            gv.validate_combo([{"type": "file", "url": "x"},
                               {"type": "link", "url": "y"}])

    def test_valid_r2v_combo(self):
        gv.validate_combo([{"type": "reference_image", "url": "x"},
                           {"type": "reference_audio", "url": "y"}])

    def test_ref_image_limit_10(self):
        with pytest.raises(ValueError):
            gv.validate_combo([{"type": "reference_image", "url": "x"}] * 11)

    def test_double_first_frame_rejected(self):
        with pytest.raises(ValueError):
            gv.validate_combo([{"type": "first_frame", "url": "x"},
                               {"type": "first_frame", "url": "y"}])


class TestParameters:
    def _args(self, **kw):
        class A:
            resolution = "720P"; ratio = "adaptive"; duration = 5
            audio = True; watermark = False; prompt_extend = False; seed = None
        a = A()
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def test_defaults(self):
        p = gv.build_parameters(self._args(), [])
        assert p == {"resolution": "720P", "ratio": "adaptive", "duration": 5,
                     "audio": True, "watermark": False, "prompt_extend": False}

    def test_duration_range(self):
        with pytest.raises(ValueError):
            gv.build_parameters(self._args(duration=31), [])
        with pytest.raises(ValueError):
            gv.build_parameters(self._args(duration=1), [])
        assert gv.build_parameters(self._args(duration=-1), [])["duration"] == -1
        assert gv.build_parameters(self._args(duration=30), [])["duration"] == 30

    def test_doc_forces_prompt_extend(self):
        p = gv.build_parameters(self._args(), [{"type": "link", "url": "https://x"}])
        assert p["prompt_extend"] is True

    def test_seed_bounds(self):
        with pytest.raises(ValueError):
            gv.build_parameters(self._args(seed=2147483648), [])
        assert gv.build_parameters(self._args(seed=0), [])["seed"] == 0


class TestFallbackDetection:
    def test_model_not_exist_triggers(self):
        assert gv.model_unavailable(
            {"http": 400, "json": {"code": "InvalidParameter",
                                   "message": "Model not exist"}}) is True

    def test_content_block_does_not_trigger(self):
        assert gv.model_unavailable(
            {"http": 400, "json": {"code": "DataInspectionFailed",
                                   "message": "content blocked"}}) is False

    def test_success_never_triggers(self):
        assert gv.model_unavailable({"http": 200, "json": {}}) is False