"""Simulator-neutral cavity and free-surface measurements for task10 probes."""
import numpy as np


def cavity_metrics(local_points, item, *, surface_radius_m=0., measure_surface=True):
    points = np.asarray(local_points, dtype=float).reshape(-1, 3)
    finite = np.isfinite(points).all(axis=1)
    good = points[finite]
    profile = np.asarray(item['cavity_profile_local_m'], dtype=float)
    if len(profile) < 2 or np.any(np.diff(profile[:, 0]) < 0):
        raise ValueError('Ordered source-derived cavity profile required')
    z = good[:, 2]
    radial_excess = np.linalg.norm(good[:, :2], axis=1) - np.interp(z, profile[:, 0], profile[:, 1])
    lower = item.get('numerical_liquid_floor_local_z_m',item['lower_flux_boundary_local_z_m'])
    upper = item['upper_flux_boundary_local_z_m']
    z_slop = item['containment_z_slop_m']
    outside = ((radial_excess > item['containment_radial_slop_m'])
               | (z < lower-z_slop) | (z > upper+z_slop))
    count = int(outside.sum() + (~finite).sum())
    surface = float(np.quantile(z, .995) + surface_radius_m) if len(z) and measure_surface else None
    error = surface-item['reference_visible_surface_local_z_m'] if surface is not None else None
    return {'count': len(points), 'nonfinite_count': int((~finite).sum()),
            'outside_count': count, 'contained': bool(len(points) and count == 0),
            'below_boundary_count': int((z < lower-z_slop).sum()),
            'below_flux_boundary_count': int((z < item['lower_flux_boundary_local_z_m']-z_slop).sum()),
            'above_boundary_count': int((z > upper+z_slop).sum()),
            'radial_excess_max_m': float(radial_excess.max()) if len(z) else None,
            'estimated_surface_local_z_m': surface, 'surface_height_error_m': error,
            'surface_height_pass': bool(finite.all() and error is not None
                                       and abs(error) <= item['surface_height_tolerance_m'])}
