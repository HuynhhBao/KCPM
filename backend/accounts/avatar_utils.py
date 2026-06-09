from django.urls import reverse


def build_user_avatar_url(user, request=None):
    if not user:
        return ''

    avatar_url = (
        getattr(user, 'avatar_url', '') or ''
    ).strip()

    if avatar_url:
        return avatar_url

    avatar_data = getattr(
        user,
        'avatar_data',
        None,
    )

    if avatar_data:
        version = ''

        avatar_updated_at = getattr(
            user,
            'avatar_updated_at',
            None,
        )

        if avatar_updated_at:
            version = (
                f'?v={int(avatar_updated_at.timestamp())}'
            )

        path = reverse(
            'user-avatar',
            kwargs={
                'user_id': user.id,
            },
        )

        url = f'{path}{version}'

        if request:
            return request.build_absolute_uri(url)

        return url

    avatar = getattr(
        user,
        'avatar',
        None,
    )

    if avatar:
        try:
            url = avatar.url
        except ValueError:
            return ''

        if request:
            return request.build_absolute_uri(url)

        return url

    return ''