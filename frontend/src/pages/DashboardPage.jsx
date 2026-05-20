import React, { useEffect, useMemo, useState } from "react";

const gatewayUrl = import.meta.env.VITE_API_GATEWAY_URL || "http://localhost:32025";

const emptyState = {
  event: {
    event_id: "EV-CONCERT-001",
    title: "Event",
    category: "music",
    city: "Moscow",
    venue: "Venue",
    capacity: 0,
    ticket_types: [],
  },
  availability: { sold_total: 0, remaining_capacity: 0, tickets: [] },
  sponsors: { total_contribution_rub: 0, items: [] },
  analytics_report: {
    sales: { tickets_sold: 0, revenue_rub: 0, occupancy_rate: 0 },
    performance: { avg_purchase_seconds: 0, purchase_target_seconds: 3 },
  },
  platform_kpi: { estimated_bookings_per_min: 0, target_bookings_per_min: 1000, max_events_supported: 1000000 },
  recommendations: { items: [] },
  feedback: { items: [] },
};

async function fetchDashboard(eventId) {
  const response = await fetch(`${gatewayUrl}/dashboard/${eventId}`);
  if (!response.ok) {
    throw new Error(`Dashboard fetch failed with ${response.status}`);
  }
  return response.json();
}

async function purchaseTicket(requestPayload) {
  const response = await fetch(`${gatewayUrl}/workflow/purchase-ticket`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestPayload),
  });
  if (!response.ok) {
    throw new Error(`Purchase failed with ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const [eventId, setEventId] = useState("EV-CONCERT-001");
  const [dashboard, setDashboard] = useState(emptyState);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [workflowResult, setWorkflowResult] = useState(null);
  const [form, setForm] = useState({
    user_id: "user-demo",
    ticket_type_id: "REGULAR",
    quantity: 1,
    promo_code: "",
    stripe_token: "tok_demo_success",
  });

  useEffect(() => {
    let active = true;
    setStatus("loading");
    fetchDashboard(eventId)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDashboard({ ...emptyState, ...payload });
        setStatus("ready");
        setError(null);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        setStatus("failed");
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [eventId]);

  const occupancyPct = useMemo(
    () => Math.round((dashboard.analytics_report?.sales?.occupancy_rate || 0) * 100),
    [dashboard.analytics_report]
  );

  const handleBuy = async () => {
    try {
      setBusy(true);
      setError(null);
      const payload = {
        user_id: form.user_id,
        event_id: eventId,
        ticket_type_id: form.ticket_type_id,
        quantity: Number(form.quantity),
        promo_code: form.promo_code || null,
        payment_method: "card",
        stripe_token: form.stripe_token || null,
      };
      const result = await purchaseTicket(payload);
      setWorkflowResult(result);
      const fresh = await fetchDashboard(eventId);
      setDashboard({ ...emptyState, ...fresh });
      setStatus("ready");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="noise" />
      <header className="hero">
        <div>
          <p className="eyebrow">EventMaster</p>
          <h1>Платформа управления событиями и билетами</h1>
          <p>
            Конференции, концерты, спорт, вебинары и выставки в одном контуре с продажами, аналитикой и участниками.
          </p>
          <div className="pill-row">
            <span>Dynamic Pricing</span>
            <span>Event Recommendations</span>
            <span>Seat Selection</span>
            <span>Async E-Tickets</span>
          </div>
        </div>
        <div className="hero-card">
          <label>
            Event ID
            <input value={eventId} onChange={(event) => setEventId(event.target.value)} />
          </label>
          <p className="status">Status: {status}</p>
          <p className="muted">{dashboard.event?.title}</p>
          <p className="muted">
            {dashboard.event?.city} • {dashboard.event?.venue}
          </p>
        </div>
      </header>

      <section className="kpi-grid">
        <article className="kpi">
          <h3>Заполняемость</h3>
          <strong>{occupancyPct}%</strong>
          <small>Продано: {dashboard.analytics_report?.sales?.tickets_sold || 0}</small>
        </article>
        <article className="kpi">
          <h3>Выручка</h3>
          <strong>{Math.round(dashboard.analytics_report?.sales?.revenue_rub || 0).toLocaleString()} ₽</strong>
          <small>По текущему мероприятию</small>
        </article>
        <article className="kpi">
          <h3>Время покупки</h3>
          <strong>{dashboard.analytics_report?.performance?.avg_purchase_seconds || 0} сек</strong>
          <small>Цель &lt; {dashboard.analytics_report?.performance?.purchase_target_seconds || 3} сек</small>
        </article>
        <article className="kpi">
          <h3>Пропускная способность</h3>
          <strong>{dashboard.platform_kpi?.estimated_bookings_per_min || 0}/мин</strong>
          <small>Цель: {dashboard.platform_kpi?.target_bookings_per_min || 1000}/мин</small>
        </article>
      </section>

      {error ? <div className="alert">{error}</div> : null}

      <section className="grid">
        <article className="panel">
          <h2>Покупка билета</h2>
          <div className="form-grid">
            <label>
              User ID
              <input value={form.user_id} onChange={(event) => setForm({ ...form, user_id: event.target.value })} />
            </label>
            <label>
              Ticket Type
              <input
                value={form.ticket_type_id}
                onChange={(event) => setForm({ ...form, ticket_type_id: event.target.value })}
              />
            </label>
            <label>
              Quantity
              <input
                type="number"
                min="1"
                max="10"
                value={form.quantity}
                onChange={(event) => setForm({ ...form, quantity: event.target.value })}
              />
            </label>
            <label>
              Promo code
              <input value={form.promo_code} onChange={(event) => setForm({ ...form, promo_code: event.target.value })} />
            </label>
            <label>
              Stripe token
              <input
                value={form.stripe_token}
                onChange={(event) => setForm({ ...form, stripe_token: event.target.value })}
              />
            </label>
          </div>
          <button onClick={handleBuy} disabled={busy}>
            {busy ? "Processing..." : "Купить билет"}
          </button>
          {workflowResult ? (
            <div className="result-box">
              <p>
                Reservation: <strong>{workflowResult.reservation?.reservation_id}</strong>
              </p>
              <p>
                Payment status: <strong>{workflowResult.payment?.status}</strong>
              </p>
              <p>
                Tickets issued: <strong>{workflowResult.tickets?.length || 0}</strong>
              </p>
              <p>
                Workflow time: <strong>{workflowResult.duration_ms} ms</strong>
              </p>
            </div>
          ) : null}
        </article>

        <article className="panel">
          <h2>Тарифы и квоты</h2>
          <div className="list">
            {(dashboard.availability?.tickets || []).map((item) => (
              <div className="list-item" key={item.ticket_type_id}>
                <div>
                  <p>{item.name}</p>
                  <small>{item.ticket_type_id}</small>
                </div>
                <div>
                  <strong>{item.remaining}</strong>
                  <small>из {item.quota}</small>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>Спонсоры</h2>
          <p className="muted">Общий вклад: {Math.round(dashboard.sponsors?.total_contribution_rub || 0).toLocaleString()} ₽</p>
          <div className="list">
            {(dashboard.sponsors?.items || []).map((item) => (
              <div className="list-item" key={item.sponsor_id}>
                <div>
                  <p>{item.name}</p>
                  <small>{item.tier}</small>
                </div>
                <strong>{Math.round(item.contribution_rub).toLocaleString()} ₽</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>Рекомендации</h2>
          <div className="pill-row">
            {(dashboard.recommendations?.items || []).map((id) => (
              <span key={id}>{id}</span>
            ))}
          </div>
          <h3>Отзывы</h3>
          <div className="list">
            {(dashboard.feedback?.items || []).slice(-3).map((item) => (
              <div className="list-item" key={item.feedback_id}>
                <div>
                  <p>{item.sentiment}</p>
                  <small>Оценка: {item.rating}</small>
                </div>
                <small>{item.comment}</small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
