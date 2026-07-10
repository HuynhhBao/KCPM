import pytest
from io import BytesIO
from PIL import Image
from accounts.cloudinary_storage import _normalize_avatar_image


def _make_image_file(mode='RGB', size=(100, 100), color=None):
    """
    Helper: create an in-memory image file in the given PIL mode.
    Returns a BytesIO object seeked to position 0.
    """
    if color is None:
        color = (255, 0, 0) if mode == 'RGB' else \
                (255, 0, 0, 128) if mode == 'RGBA' else \
                (128,) if mode == 'L' else \
                (255, 0, 0)

    img = Image.new(mode, size, color)
    buf = BytesIO()
    # Save as PNG to preserve mode (JPEG doesn't support RGBA/P)
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


class TestNormalizeAvatarImage:
    """
    White-box tests for _normalize_avatar_image() — lines 61–103 (cloudinary_storage.py)

    Covers:
      - Branch 1 (lines 67–68): image.mode not in ('RGB', 'RGBA')
                                  → convert to RGBA first, then composite onto white background
      - Branch 2 (lines 70–82): image.mode == 'RGBA'
                                  → paste onto white RGB background → image becomes RGB
      - Branch 3 (lines 83–84): image.mode == 'RGB'
                                  → convert directly to RGB (no-op effectively)
      - Happy path (lines 86–103): thumbnail resize, save as WEBP, return BytesIO with name
    """

    # ------------------------------------------------------------------
    # Branch 1 — lines 67–68  (mode not RGB/RGBA → convert to RGBA)
    # ------------------------------------------------------------------

    def test_TC1_branch1_hit_grayscale_L_mode(self):
        """
        Tests lines 67–68 (Branch 1 — HIT: mode = 'L').
        Condition: uploaded image is grayscale (mode='L') → not in ('RGB','RGBA')
        Expected : converted to RGBA first, then composited onto white → final output is WEBP RGB
        """
        buf = _make_image_file(mode='L', color=(128,))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    def test_TC2_branch1_hit_palette_P_mode(self):
        """
        Tests lines 67–68 (Branch 1 — HIT: mode = 'P' / palette).
        Condition: uploaded image is palette mode → not in ('RGB','RGBA')
        Expected : converted to RGBA, then composited → final output is WEBP RGB
        """
        img = Image.new('RGB', (100, 100), (0, 255, 0))
        img_p = img.convert('P')
        buf = BytesIO()
        img_p.save(buf, format='PNG')
        buf.seek(0)
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    def test_TC3_branch1_hit_LA_mode(self):
        """
        Tests lines 67–68 (Branch 1 — HIT: mode = 'LA' grayscale with alpha).
        Condition: uploaded image is 'LA' mode → not in ('RGB','RGBA')
        Expected : converted to RGBA, then composited → final output is WEBP RGB
        """
        img = Image.new('LA', (100, 100), (128, 200))
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    def test_TC4_branch1_miss_rgb_mode(self):
        """
        Tests lines 67–68 (Branch 1 — MISS: mode = 'RGB').
        Condition: image.mode = 'RGB' → in ('RGB','RGBA') → branch 1 not taken
        Expected : no conversion to RGBA; goes directly to else branch (Branch 3)
        """
        buf = _make_image_file(mode='RGB')
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    def test_TC5_branch1_miss_rgba_mode(self):
        """
        Tests lines 67–68 (Branch 1 — MISS: mode = 'RGBA').
        Condition: image.mode = 'RGBA' → in ('RGB','RGBA') → branch 1 not taken
        Expected : goes directly to Branch 2 (RGBA composite)
        """
        buf = _make_image_file(mode='RGBA', color=(255, 0, 0, 128))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    # ------------------------------------------------------------------
    # Branch 2 — lines 70–82  (mode == 'RGBA' → composite onto white background)
    # ------------------------------------------------------------------

    def test_TC6_branch2_hit_rgba_composited_onto_white(self):
        """
        Tests lines 70–82 (Branch 2 — HIT).
        Condition: image.mode = 'RGBA' → paste onto white RGB background
        Expected : result image mode is RGB (alpha channel removed via compositing)
        """
        buf = _make_image_file(mode='RGBA', color=(0, 0, 255, 200))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    def test_TC7_branch2_hit_rgba_fully_transparent(self):
        """
        Tests lines 70–82 (Branch 2 — HIT: fully transparent RGBA).
        Condition: image.mode = 'RGBA', alpha = 0 → composited onto white → white result
        Expected : output is WEBP RGB (transparent pixels become white)
        """
        buf = _make_image_file(mode='RGBA', color=(255, 0, 0, 0))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    def test_TC8_branch2_miss_rgb_skips_composite(self):
        """
        Tests lines 70–82 (Branch 2 — MISS: mode = 'RGB').
        Condition: image.mode = 'RGB' → `if image.mode == 'RGBA'` is False → goes to else
        Expected : no white background compositing; image.convert('RGB') called instead
        """
        buf = _make_image_file(mode='RGB', color=(100, 150, 200))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    # ------------------------------------------------------------------
    # Branch 3 — lines 83–84  (mode == 'RGB' → convert directly to RGB)
    # ------------------------------------------------------------------

    def test_TC9_branch3_hit_rgb_convert_direct(self):
        """
        Tests lines 83–84 (Branch 3 — HIT).
        Condition: image.mode = 'RGB' → else branch → image.convert('RGB')
        Expected : output is WEBP RGB; no compositing performed
        """
        buf = _make_image_file(mode='RGB', color=(200, 100, 50))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    def test_TC10_branch3_miss_rgba_takes_if_branch(self):
        """
        Tests lines 83–84 (Branch 3 — MISS: mode = 'RGBA' → if branch taken, not else).
        Condition: image.mode = 'RGBA' → `if image.mode == 'RGBA'` is True → else not reached
        Expected : compositing path taken; output is still WEBP RGB
        """
        buf = _make_image_file(mode='RGBA', color=(50, 100, 200, 255))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
        assert output_img.mode == 'RGB'

    # ------------------------------------------------------------------
    # Happy path — lines 86–103  (thumbnail + save WEBP + return BytesIO)
    # ------------------------------------------------------------------

    def test_TC11_happy_path_output_is_bytesio_with_name(self):
        """
        Tests lines 91–102 (Happy path — return value).
        Condition: valid RGB image
        Expected : returns BytesIO object with .name = 'avatar.webp', seeked to 0
        """
        buf = _make_image_file(mode='RGB')
        result = _normalize_avatar_image(buf)
        assert isinstance(result, __import__('io').BytesIO)
        assert result.name == 'avatar.webp'
        assert result.tell() == 0

    def test_TC12_happy_path_thumbnail_max_512(self):
        """
        Tests lines 86–89 (Happy path — thumbnail resize).
        Condition: large image (1024x1024) → thumbnail reduces to max 512x512
        Expected : output image dimensions <= 512 on both axes
        """
        buf = _make_image_file(mode='RGB', size=(1024, 1024))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.width <= 512
        assert output_img.height <= 512

    def test_TC13_happy_path_small_image_not_upscaled(self):
        """
        Tests lines 86–89 (Happy path — thumbnail does not upscale).
        Condition: small image (50x50) → thumbnail keeps original size
        Expected : output image dimensions remain 50x50 (thumbnail never upscales)
        """
        buf = _make_image_file(mode='RGB', size=(50, 50))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.width == 50
        assert output_img.height == 50

    def test_TC14_happy_path_output_is_valid_webp(self):
        """
        Tests lines 93–98 (Happy path — saved as WEBP format).
        Condition: any valid image input
        Expected : output BytesIO contains valid WEBP image data
        """
        buf = _make_image_file(mode='RGBA', color=(10, 20, 30, 255))
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'

    def test_TC15_happy_path_seek_reset_before_open(self):
        """
        Tests line 62 (Happy path — seek(0) called on input before Image.open).
        Condition: uploaded_file is seeked to end before passing in
        Expected : function resets seek position; image opens successfully
        """
        buf = _make_image_file(mode='RGB')
        buf.seek(0, 2)  # seek to end
        result = _normalize_avatar_image(buf)
        output_img = Image.open(result)
        assert output_img.format == 'WEBP'
