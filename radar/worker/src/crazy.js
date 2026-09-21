/**
 * What makes a move worth interrupting someone for.
 *
 * The first version of this counted wallets and called four of them
 * remarkable. Against two days of this radar's own history, four wallets on
 * one token happens to 6.6% of every token that passes through — roughly as
 * remarkable as rain. Both alerts it ever sent were rugs.
 *
 * So the bars here are read off that history rather than chosen. Eight
 * independent people inside ten minutes is the top 0.85%. A median buy is
 * 1.6 SOL, so twenty-five SOL of conviction is many times a normal one. And
 * a buy several times larger than that wallet's OWN usual size is the top
 * 2.3% of all buys — which is what "unusual" has to mean, because 5 SOL is
 * nothing from a wallet that always sends 5 and everything from one that
 * never does.
 */

/**
 * People, not wallets. Two wallets called "Mort" and "mort" buying three
 * seconds apart are one person with two windows open, and counting them
 * twice is how one operator cleared a gate that asked for two.
 */
export function operator(name) {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "") || name;
}

export function operators(buyers) {
  return new Set(buyers.map((b) => operator(b.name)));
}

/**
 * A wallet that buys everything is evidence of nothing. Its presence in a
 * cluster says only that it was awake.
 */
export function isSprayer(name, buyCounts, limit) {
  return (buyCounts.get(operator(name)) || 0) > limit;
}

/** A buy several times the wallet's own normal size is the wallet shouting. */
export function oversized(buyers, medians, multiple) {
  return buyers.filter((b) => {
    const med = medians.get(b.name);
    return med > 0 && b.sol >= multiple * med;
  }).length;
}
