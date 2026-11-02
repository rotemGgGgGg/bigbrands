"""Geocentric ecliptic longitudes (degrees) of Sun, Moon, Mercury..Neptune for any UTC time, no packages.
Planets: JPL 'Approximate Positions of the Planets' Keplerian elements, valid 1800-2050 (error < ~1 deg for the inner planets,
fractions of a degree for the outer ones). Moon: Meeus ch.47 main periodic terms (~0.3 deg). Good enough for 1-degree aspect orbs."""
import numpy as np
EL = {  # a, e, I, L, long.peri, long.node  and their rates per Julian century
    "mercury": ([0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593], [0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081]),
    "venus": ([0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255], [0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418]),
    "earth": ([1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0], [0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0]),
    "mars": ([1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891], [0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343]),
    "jupiter": ([5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909], [-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106]),
    "saturn": ([9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448], [-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794]),
    "uranus": ([19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503], [-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589]),
    "neptune": ([30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574], [0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664]),
}
R = np.pi / 180


def helio(name, T):
    e0, r = EL[name]; a, e, I, L, wb, Om = [np.asarray(x0 + x1 * T, float) for x0, x1 in zip(e0, r)]
    w = wb - Om; M = np.mod(L - wb + 180, 360) - 180; E = M + (180 / np.pi) * e * np.sin(M * R)
    for _ in range(6): E = E - (E - (180 / np.pi) * e * np.sin(E * R) - M) / (1 - e * np.cos(E * R))
    xp = a * (np.cos(E * R) - e); yp = a * np.sqrt(1 - e * e) * np.sin(E * R)
    cw, sw, cO, sO, cI, sI = np.cos(w * R), np.sin(w * R), np.cos(Om * R), np.sin(Om * R), np.cos(I * R), np.sin(I * R)
    x = (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp
    y = (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp
    return x, y


def moon(T):
    Lp = 218.3164477 + 481267.88123421 * T; D = 297.8501921 + 445267.1114034 * T; M = 357.5291092 + 35999.0502909 * T
    Mp = 134.9633964 + 477198.8675055 * T; F = 93.2720950 + 483202.0175233 * T; s = lambda x: np.sin(x * R)
    return np.mod(Lp + 6.288774 * s(Mp) + 1.274027 * s(2 * D - Mp) + 0.658314 * s(2 * D) + 0.213618 * s(2 * Mp) - 0.185116 * s(M)
                  - 0.114332 * s(2 * F) + 0.058793 * s(2 * D - 2 * Mp) + 0.057066 * s(2 * D - M - Mp) + 0.053322 * s(2 * D + Mp)
                  + 0.045758 * s(2 * D - M) - 0.040923 * s(M - Mp) - 0.034720 * s(D) - 0.030383 * s(M + Mp), 360)


def longitudes(utc):
    """utc: pandas DatetimeIndex (naive UTC). Returns dict body -> longitude array (deg, geocentric, ecliptic of date approx)."""
    jd = utc.to_julian_date().values; T = (jd - 2451545.0) / 36525
    ex, ey = helio("earth", T); out = {"sun": np.mod(np.degrees(np.arctan2(-ey, -ex)), 360), "moon": moon(T)}
    for p in ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"):
        x, y = helio(p, T); out[p] = np.mod(np.degrees(np.arctan2(y - ey, x - ex)), 360)
    return out
