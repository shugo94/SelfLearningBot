import { useEffect, useState } from "react";
import { api, type BrokerStatus } from "../api/client";

interface Props {
  onStatusChange?: (s: BrokerStatus) => void;
}

export default function SettingsPanel({ onStatusChange }: Props) {
  const [status, setStatus] = useState<BrokerStatus | null>(null);
  const [form, setForm] = useState({ api_key: "", client_id: "", password: "", totp_secret: "" });
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  const refresh = () => {
    api.brokerStatus().then((s) => { setStatus(s); onStatusChange?.(s); }).catch((e) => setErr(String(e)));
  };
  useEffect(refresh, []);

  const save = async () => {
    setErr(null); setSaving(true);
    try {
      const s = await api.saveBrokerCreds(form);
      setStatus(s); onStatusChange?.(s);
      setForm({ api_key: "", client_id: "", password: "", totp_secret: "" });
    } catch (e) { setErr(String(e)); }
    finally { setSaving(false); }
  };

  const test = async () => {
    setErr(null); setTesting(true); setTestResult("");
    try {
      const r = await api.testBroker();
      setTestResult(`✓ ${r.message}  (sample: ${r.sample_quote.symbol} @ ₹${r.sample_quote.price.toFixed(2)})`);
      refresh();
    } catch (e) {
      setTestResult(`✗ ${e}`);
      refresh();
    }
    finally { setTesting(false); }
  };

  const remove = async () => {
    if (!confirm("Delete stored credentials? The app will fall back to Yahoo Finance.")) return;
    await api.deleteBrokerCreds();
    refresh();
  };

  const fieldsValid = form.api_key && form.client_id && form.password && form.totp_secret;

  return (
    <>
      <div className="header">
        <h2>Settings — Broker Credentials</h2>
        {status && (
          <span className="badge" style={{ background: status.configured ? "rgba(46, 204, 113, 0.15)" : undefined,
                                            color: status.configured ? "var(--green)" : undefined }}>
            active: {status.active_source}
          </span>
        )}
      </div>

      {err && <div className="error">{err}</div>}

      <div className="grid grid-2" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="card">
          <h3>Angel One SmartAPI</h3>
          <p className="sub" style={{ marginTop: 0 }}>
            Required for live NSE/BSE quotes. Get an API key from the{" "}
            <a href="https://smartapi.angelbroking.com" target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
              SmartAPI portal
            </a>. The TOTP secret is the base32 string you copy when setting up 2FA — NOT the rotating 6-digit code.
          </p>

          <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
            <Field
              label="API Key"
              value={form.api_key}
              onChange={(v) => setForm({ ...form, api_key: v })}
              placeholder={status?.api_key_preview ?? "e.g. AbCdEf123"}
              type="password"
            />
            <Field
              label="Client ID"
              value={form.client_id}
              onChange={(v) => setForm({ ...form, client_id: v })}
              placeholder={status?.client_id ?? "e.g. S1234567"}
            />
            <Field
              label="Password / MPIN"
              value={form.password}
              onChange={(v) => setForm({ ...form, password: v })}
              placeholder="••••"
              type="password"
            />
            <Field
              label="TOTP Secret (base32)"
              value={form.totp_secret}
              onChange={(v) => setForm({ ...form, totp_secret: v })}
              placeholder={status?.totp_secret_preview ?? "e.g. JBSWY3DPEHPK3PXP"}
              type="password"
            />
          </div>

          <div className="row" style={{ marginTop: 14 }}>
            <button className="primary" onClick={save} disabled={!fieldsValid || saving}>
              {saving ? "Saving…" : status?.configured ? "Update credentials" : "Save credentials"}
            </button>
            <button onClick={test} disabled={!status?.configured || testing}>
              {testing ? "Testing…" : "Test connection"}
            </button>
            {status?.configured && (
              <button onClick={remove} style={{ color: "var(--red)" }}>Delete</button>
            )}
          </div>
          {testResult && (
            <div className="sub" style={{ marginTop: 10, color: testResult.startsWith("✓") ? "var(--green)" : "var(--red)" }}>
              {testResult}
            </div>
          )}
        </div>

        <div className="card">
          <h3>Current Status</h3>
          {!status ? <div className="empty">Loading…</div> : (
            <table>
              <tbody>
                <tr><td>Active data source</td><td className="num">{status.active_source}</td></tr>
                <tr><td>Configured</td><td className="num">{status.configured ? "yes" : "no"}</td></tr>
                {status.configured && (<>
                  <tr><td>API key</td><td className="num">{status.api_key_preview}</td></tr>
                  <tr><td>Client ID</td><td className="num">{status.client_id}</td></tr>
                  <tr><td>TOTP secret</td><td className="num">{status.totp_secret_preview}</td></tr>
                  <tr><td>Last successful login</td><td className="num">{status.last_login_at ? new Date(status.last_login_at).toLocaleString() : "never"}</td></tr>
                  <tr><td>Last error</td><td className="num" style={{ color: status.last_error ? "var(--red)" : undefined }}>{status.last_error ?? "—"}</td></tr>
                </>)}
              </tbody>
            </table>
          )}
          <div className="sub" style={{ marginTop: 12, padding: 10, background: "var(--panel-2)", borderRadius: 6 }}>
            <strong>Security note:</strong> credentials are stored unencrypted in{" "}
            <code>data/selflearningbot.db</code> on this machine. The file is in <code>.gitignore</code>.
            Anyone with access to your home folder can read it — don't use this on a shared machine.
          </div>
        </div>
      </div>
    </>
  );
}

function Field({ label, value, onChange, placeholder, type = "text" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string;
}) {
  return (
    <div>
      <div className="sub" style={{ marginBottom: 4 }}>{label}</div>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ width: "100%" }}
        autoComplete="off"
        spellCheck={false}
      />
    </div>
  );
}
