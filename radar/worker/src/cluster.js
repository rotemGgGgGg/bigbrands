/**
 * Cluster state.
 *
 * A cluster is only a cluster if the buys are seen together, and the worker
 * has no single place to see them: requests scatter across instances, and the
 * database's free daily allowance can run out mid-day. One Durable Object is
 * that single place — every buy goes through it, so the roster it returns is
 * the whole roster, and each alert is claimed exactly once.
 *
 * It answers in one round trip because the alert path is latency-bound.
 */
export class ClusterState {
  constructor(state) {
    this.sql = state.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS buys (
      mint TEXT NOT NULL, wallet TEXT NOT NULL, name TEXT NOT NULL,
      sol REAL NOT NULL, ts INTEGER NOT NULL, is_signal INTEGER NOT NULL,
      PRIMARY KEY (mint, wallet))`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS claims (
      key TEXT PRIMARY KEY, ts INTEGER NOT NULL)`);
  }

  /** Grants a key to exactly one caller within the retention window. */
  claim(key, now) {
    const held = [...this.sql.exec("SELECT key FROM claims WHERE key = ?", key)];
    if (held.length) return false;
    this.sql.exec("INSERT INTO claims (key, ts) VALUES (?, ?)", key, now);
    return true;
  }

  async fetch(request) {
    const body = await request.json();

    // A bare claim, for a decision the worker can only make after asking
    // somewhere else — the Legends gate, which needs a market cap first.
    if (body.claimKey) {
      return Response.json({ granted: this.claim(body.claimKey, Date.now()) });
    }
    const buy = body;
    const now = Date.now();

    // Anything older than the window can no longer join a cluster. Claims
    // outlive it, so a cluster that keeps growing is not re-announced.
    this.sql.exec("DELETE FROM buys WHERE ts < ?", now - buy.windowMs);
    this.sql.exec("DELETE FROM claims WHERE ts < ?", now - buy.windowMs * 6);

    // First writer for a (mint, wallet) wins; a re-buy does not re-add.
    this.sql.exec(
      "INSERT OR IGNORE INTO buys (mint, wallet, name, sol, ts, is_signal) VALUES (?, ?, ?, ?, ?, ?)",
      buy.mint, buy.wallet, buy.name, buy.sol, now, buy.isSignal ? 1 : 0,
    );

    const buyers = [...this.sql.exec(
      "SELECT wallet, name, sol, ts, is_signal FROM buys WHERE mint = ? ORDER BY ts", buy.mint,
    )].map((r) => ({
      wallet: r.wallet, name: r.name, sol: r.sol, ts: r.ts, isSignal: r.is_signal === 1,
    }));

    return Response.json({
      buyers,
      singleClaim: buy.isSignal && this.claim(`single:${buy.wallet}:${buy.mint}`, now),
      clusterClaim: buyers.length >= buy.minCluster
        && this.claim(`cluster:${buy.mint}:${buyers.length}`, now),
    });
  }
}
