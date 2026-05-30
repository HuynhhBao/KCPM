import uuid
from io import BytesIO

import cloudinary
import cloudinary.uploader
from decouple import config
from django.utils import timezone
from PIL import Image, ImageOps


_CLOUDINARY_CONFIGURED = False


def configure_cloudinary():
    global _CLOUDINARY_CONFIGURED

    if _CLOUDINARY_CONFIGURED:
        return

    cloud_name = config(
        'CLOUDINARY_CLOUD_NAME',
        default='',
    ).strip()

    api_key = config(
        'CLOUDINARY_API_KEY',
        default='',
    ).strip()

    api_secret = config(
        'CLOUDINARY_API_SECRET',
        default='',
    ).strip()

    if not cloud_name:
        raise RuntimeError(
            'Thiếu biến môi trường CLOUDINARY_CLOUD_NAME'
        )

    if not api_key:
        raise RuntimeError(
            'Thiếu biến môi trường CLOUDINARY_API_KEY'
        )

    if not api_secret:
        raise RuntimeError(
            'Thiếu biến môi trường CLOUDINARY_API_SECRET'
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

    _CLOUDINARY_CONFIGURED = True


def _normalize_avatar_image(uploaded_file):
    uploaded_file.seek(0)

    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)

    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGBA')

    if image.mode == 'RGBA':
        background = Image.new(
            'RGB',
            image.size,
            (255, 255, 255),
        )

        background.paste(
            image,
            mask=image.split()[-1],
        )

        image = background
    else:
        image = image.convert('RGB')

    image.thumbnail(
        (512, 512),
        Image.Resampling.LANCZOS,
    )

    output = BytesIO()

    image.save(
        output,
        format='WEBP',
        quality=85,
        method=6,
    )

    output.seek(0)
    output.name = 'avatar.webp'

    return output


def upload_user_avatar(
    *,
    user,
    uploaded_file,
):
    if not user:
        raise ValueError(
            'Thiếu user khi upload avatar'
        )

    if not uploaded_file:
        raise ValueError(
            'Thiếu file avatar'
        )

    configure_cloudinary()

    now = timezone.now()
    timestamp = int(now.timestamp())

    public_id = (
        f'chung_vi/avatars/users/{user.id}/'
        f'avatar_{timestamp}_{uuid.uuid4().hex}'
    )

    normalized_file = _normalize_avatar_image(
        uploaded_file,
    )

    result = cloudinary.uploader.upload(
        normalized_file,
        public_id=public_id,
        resource_type='image',
        format='webp',
        overwrite=False,
        invalidate=True,
    )

    secure_url = (
        result.get('secure_url') or ''
    ).strip()

    uploaded_public_id = (
        result.get('public_id') or ''
    ).strip()

    if not secure_url or not uploaded_public_id:
        raise RuntimeError(
            'Upload avatar lên Cloudinary thất bại'
        )

    return {
        'avatar_url': secure_url,
        'avatar_storage_path': uploaded_public_id,
        'avatar_updated_at': now,
    }


def delete_cloudinary_avatar_safely(public_id):
    if not public_id:
        return

    try:
        configure_cloudinary()

        cloudinary.uploader.destroy(
            public_id,
            resource_type='image',
            invalidate=True,
        )

    except Exception:
        pass