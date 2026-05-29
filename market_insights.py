{% extends 'base.html' %}
{% block title %}Market Insights{% endblock %}
{% block page_title %}Market Insights{% endblock %}

{% block content %}

<div class="ph">
  <div>
    <div class="ph-title">Market Insights</div>
    <div class="ph-sub">Current prices, demand trends, stock movement, and sales signals</div>
  </div>
  {% if current_user.role == 'farmer' %}
    <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">
      <svg viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg>
      Dashboard
    </a>
  {% endif %}
</div>

<div class="grid g4 mb-6">
  <div class="stat">
    <div class="stat-icon si-green">
      <svg viewBox="0 0 24 24"><path d="M3 3h18v18H3z"/><path d="M7 8h10"/><path d="M7 12h10"/><path d="M7 16h6"/></svg>
    </div>
    <div>
      <div class="stat-lbl">Product Types</div>
      <div class="stat-val">{{ market_summary.product_types }}</div>
    </div>
    <div class="stat-note text-muted">Grouped by product name and selling unit</div>
  </div>

  <div class="stat">
    <div class="stat-icon si-blue">
      <svg viewBox="0 0 24 24"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><path d="M3.3 7L12 12l8.7-5"/></svg>
    </div>
    <div>
      <div class="stat-lbl">Available Stock</div>
      <div class="stat-val">{{ market_summary.total_stock|qty }}</div>
    </div>
    <div class="stat-note text-muted">Total listed quantity</div>
  </div>

  <div class="stat">
    <div class="stat-icon si-amber">
      <svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 14l3-3 4 4 5-7"/></svg>
    </div>
    <div>
      <div class="stat-lbl">Quantity Sold</div>
      <div class="stat-val">{{ market_summary.total_units_sold|qty }}</div>
    </div>
    <div class="stat-note text-muted">Based on transaction records</div>
  </div>

  <div class="stat">
    <div class="stat-icon si-red">
      <svg viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
    </div>
    <div>
      <div class="stat-lbl">Avg Price</div>
      <div class="stat-val">&#8369;{{ "%.2f"|format(market_summary.average_market_price) }}</div>
    </div>
    <div class="stat-note text-muted">Average across product groups</div>
  </div>
</div>

{% if market_rows %}
<div class="card ai-panel mb-6">
  <div class="card-hd">
    <span class="card-hd-title">Market AI Signals</span>
    <span class="badge b-blue">{{ market_summary.high_demand_count }} high-demand group{{ 's' if market_summary.high_demand_count != 1 }}</span>
  </div>
  <div class="card-body">
    <div class="ai-advice-list">
      {% for row in market_rows[:3] %}
        <div class="ai-advice-row ai-neutral">
          <div class="ai-advice-main">
            <div class="flex items-center gap-2">
              {% if row.demand_trend == 'High Demand' %}
                <span class="badge b-green">{{ row.demand_trend }}</span>
              {% elif row.demand_trend == 'Active Demand' %}
                <span class="badge b-blue">{{ row.demand_trend }}</span>
              {% else %}
                <span class="badge b-gray">{{ row.demand_trend }}</span>
              {% endif %}
              <span class="font-bold">{{ row.name }}</span>
            </div>
            <div class="ai-advice-title">{{ row.market_action }}</div>
            <div class="text-muted text-sm">{{ row.ai_reading }}</div>
            <div class="ai-next-step mt-2">{{ row.next_step }}</div>
          </div>
          <div class="ai-evidence">
            <span>&#8369;{{ "%.2f"|format(row.avg_price) }} / {{ row.unit }}</span>
            <span>{{ row.total_stock|qty }} {{ row.unit }} stock</span>
            <span>{{ row.order_count }} order{{ 's' if row.order_count != 1 }}</span>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</div>
{% endif %}

<div class="card">
  <div class="card-hd">
    <span class="card-hd-title">Current Market Information</span>
  </div>

  {% if market_rows %}
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Product</th>
          <th>Current Price</th>
          <th>Price Range</th>
          <th>Stock</th>
          <th>Orders</th>
          <th>Demand Trend</th>
          <th>Market Action</th>
          <th>AI Reading</th>
          <th>Revenue</th>
        </tr>
      </thead>
      <tbody>
        {% for row in market_rows %}
        <tr>
          <td data-label="Product">
            <div class="font-bold">{{ row.name }}</div>
            <div class="text-muted text-xs">{{ row.listing_count }} listing{{ 's' if row.listing_count != 1 }} from {{ row.farmer_count }} farmer{{ 's' if row.farmer_count != 1 }}</div>
          </td>
          <td data-label="Current Price"><span class="font-bold text-success">&#8369;{{ "%.2f"|format(row.avg_price) }} / {{ row.unit }}</span></td>
          <td data-label="Price Range" class="text-muted text-sm">&#8369;{{ "%.2f"|format(row.min_price) }} - &#8369;{{ "%.2f"|format(row.max_price) }} / {{ row.unit }}</td>
          <td data-label="Stock">{{ row.total_stock|qty }} <span class="text-muted text-xs">{{ row.unit }}</span></td>
          <td data-label="Orders">
            <div class="font-bold">{{ row.order_count }}</div>
            <div class="text-muted text-xs">{{ row.units_sold|qty }} {{ row.unit }} sold</div>
          </td>
          <td data-label="Demand Trend">
            {% if row.demand_trend == 'High Demand' %}
              <span class="badge b-green">{{ row.demand_trend }}</span>
            {% elif row.demand_trend == 'Active Demand' %}
              <span class="badge b-blue">{{ row.demand_trend }}</span>
            {% else %}
              <span class="badge b-gray">{{ row.demand_trend }}</span>
            {% endif %}
          </td>
          <td data-label="Market Action">
            {% if row.market_action == 'Increase supply' %}
              <span class="badge b-red">{{ row.market_action }}</span>
            {% elif row.market_action in ['Promote product', 'Monitor pricing'] %}
              <span class="badge b-amber">{{ row.market_action }}</span>
            {% elif row.market_action == 'Maintain supply' %}
              <span class="badge b-green">{{ row.market_action }}</span>
            {% else %}
              <span class="badge b-gray">{{ row.market_action }}</span>
            {% endif %}
          </td>
          <td data-label="AI Reading">
            <div class="text-sm">{{ row.ai_reading }}</div>
            <div class="ai-inline-step mt-1">{{ row.next_step }}</div>
          </td>
          <td data-label="Revenue"><span class="font-bold">&#8369;{{ "%.2f"|format(row.approved_revenue) }}</span></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
  <div class="card-body" style="text-align:center;padding:48px 24px">
    <div class="font-bold" style="margin-bottom:6px">No market data yet</div>
    <div class="text-muted text-sm">Add products and transactions to generate price and demand insights.</div>
  </div>
  {% endif %}
</div>

{% endblock %}
