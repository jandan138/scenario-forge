"""Fixed-region visual Fehling policy; time is cumulative sample/water contact time."""

POLICY_VERSION = 'visual_fixed_regions_v5'


def appearance(seconds):
    t = min(60.0, max(0.0, seconds))
    progress = max(0.0, (t - 30) / 30)
    blue, cloud, clear = (.40, .72, .95), (.65, .30, .14), (.94, .97, 1.0)
    red = (.70, .18, .07)
    if t <= 30:
        rgb, opacity = blue, .55
    elif t <= 45:
        a = (t - 30) / 15
        rgb = tuple(x + (y - x) * a for x, y in zip(blue, cloud))
        opacity = .55 + .25 * a
    else:
        a = (t - 45) / 15
        rgb = tuple(x + (y - x) * a for x, y in zip(cloud, clear))
        opacity = .80 - .55 * a
    return dict(
        progress=progress, color=rgb, opacity=opacity, roughness=.08,
        sediment=progress,
        sediment_color=tuple(x + (y - x) * progress for x, y in zip(blue, red)),
        sediment_opacity=.55 + .45 * progress,
        sediment_roughness=.08 + .57 * progress,
        reaction_stage='warming' if t <= 30 else 'clouding' if t < 45 else 'settling' if t < 60 else 'developed',
    )
