const summaryEls = {
  totalOrders: document.getElementById('totalOrders'),
  totalRevenue: document.getElementById('totalRevenue'),
  totalCustomers: document.getElementById('totalCustomers'),
  repeatCustomers: document.getElementById('repeatCustomers'),
};

const countryFilter = document.getElementById('countryFilter');
const yearFilter = document.getElementById('yearFilter');
const minSupportInput = document.getElementById('minSupport');
const minConfidenceInput = document.getElementById('minConfidence');
const resetFiltersBtn = document.getElementById('resetFilters');
const applyFiltersBtn = document.getElementById('applyFilters');
const customerSelect = document.getElementById('customerSelect');
const customerDetails = document.getElementById('customerDetails');
const rulesTableBody = document.getElementById('rulesTableBody');

let monthlyChart;
let yearlyChart;
let weeklyChart;
let customerProductChart;
let dashboardRefreshId = 0;

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Request failed');
  }
  return response.json();
}

function money(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
}

function getActiveFilters() {
  return {
    country: countryFilter.value || 'All',
    year: yearFilter.value || 'All',
    minSupport: Number(minSupportInput.value || 0.02),
    minConfidence: Number(minConfidenceInput.value || 0.5),
  };
}

function buildFilterParams() {
  const params = new URLSearchParams();
  const { country, year, minSupport, minConfidence } = getActiveFilters();

  if (country !== 'All') params.set('country', country);
  if (year !== 'All') params.set('year', year);
  params.set('min_support', String(minSupport));
  params.set('min_confidence', String(minConfidence));
  return params;
}

function renderSummary(data) {
  summaryEls.totalOrders.textContent = data.total_orders;
  summaryEls.totalRevenue.textContent = money(data.total_revenue);
  summaryEls.totalCustomers.textContent = data.total_customers;
  summaryEls.repeatCustomers.textContent = data.repeat_customers;
}

function createChart(canvasId, type, label, labels, values, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  return new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        borderColor: color,
        backgroundColor: color + '66',
        borderWidth: 2,
        tension: 0.25,
        fill: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

function renderTrends(data) {
  const monthLabels = data.monthly.map(item => item.label);
  const monthValues = data.monthly.map(item => item.value);

  const yearLabels = data.yearly.map(item => item.label);
  const yearValues = data.yearly.map(item => item.value);

  const weekLabels = data.weekly.map(item => item.label);
  const weekValues = data.weekly.map(item => item.value);

  if (monthlyChart) monthlyChart.destroy();
  if (yearlyChart) yearlyChart.destroy();
  if (weeklyChart) weeklyChart.destroy();

  monthlyChart = createChart('monthlyChart', 'line', 'Orders', monthLabels, monthValues, '#1d4ed8');
  yearlyChart = createChart('yearlyChart', 'bar', 'Orders', yearLabels, yearValues, '#10b981');
  weeklyChart = createChart('weeklyChart', 'bar', 'Orders', weekLabels, weekValues, '#f59e0b');
}

function renderCustomerDetails(data) {
  const summary = data.summary;
  customerDetails.innerHTML = `
    <div class="info-box">
      <span class="label">Customer ID</span>
      <strong>${data.customer_id}</strong>
    </div>
    <div class="info-box">
      <span class="label">Total Spending</span>
      <strong>${money(summary.TotalSpending)}</strong>
    </div>
    <div class="info-box">
      <span class="label">Orders</span>
      <strong>${summary.NumberOfOrders}</strong>
    </div>
    <div class="info-box">
      <span class="label">Avg Order</span>
      <strong>${money(summary.AverageOrderValue)}</strong>
    </div>
    <div class="info-box">
      <span class="label">Products</span>
      <strong>${summary.NumberOfProducts}</strong>
    </div>
    <div class="info-box">
      <span class="label">Country</span>
      <strong>${summary.Country}</strong>
    </div>
  `;

  if (customerProductChart) customerProductChart.destroy();

  const productNames = data.top_products.map(item => item.name);
  const productValues = data.top_products.map(item => item.value);
  customerProductChart = createChart('customerProductChart', 'doughnut', 'Products', productNames, productValues, '#1d4ed8');
}

function renderRules(rules) {
  if (rules.length === 0) {
    rulesTableBody.innerHTML = '<tr><td colspan="5">No association rules found.</td></tr>';
    return;
  }

  rulesTableBody.innerHTML = rules.map(rule => `
    <tr>
      <td>${rule.antecedent.join(', ')}</td>
      <td>${rule.consequent.join(', ')}</td>
      <td>${rule.support}</td>
      <td>${rule.confidence}</td>
      <td>${rule.lift}</td>
    </tr>
  `).join('');
}

async function loadFilterOptions() {
  const metadata = await fetchJson('/api/filters');

  countryFilter.innerHTML = metadata.countries
    .map(country => `<option value="${country}">${country}</option>`)
    .join('');
  yearFilter.innerHTML = metadata.years
    .map(year => `<option value="${year}">${year}</option>`)
    .join('');

  countryFilter.value = 'All';
  yearFilter.value = 'All';
}

async function loadCustomerOptions() {
  const params = buildFilterParams();
  const customers = await fetchJson(`/api/customers?${params.toString()}`);
  customerSelect.innerHTML = customers.map(customer => `
    <option value="${customer.customer_id}">${customer.customer_id} - ${customer.country}</option>
  `).join('');

  const firstCustomer = customers[0]?.customer_id ?? 12347;
  customerSelect.value = firstCustomer;
  await loadCustomerAnalysis(firstCustomer);
}

async function loadCustomerAnalysis(customerId) {
  const params = buildFilterParams();
  params.set('customer_id', customerId);
  const details = await fetchJson(`/api/customer-analysis?${params.toString()}`);
  renderCustomerDetails(details);
}

async function refreshDashboard() {
  const refreshId = ++dashboardRefreshId;

  try {
    const params = buildFilterParams();
    const [overview, trends] = await Promise.all([
      fetchJson(`/api/overview?${params.toString()}`),
      fetchJson(`/api/trends?${params.toString()}`),
    ]);

    renderSummary(overview);
    renderTrends(trends);
    rulesTableBody.innerHTML = '<tr><td colspan="5">Loading association rules...</td></tr>';

    fetchJson(`/api/association-rules?${params.toString()}`)
      .then(rules => {
        if (refreshId === dashboardRefreshId) renderRules(rules);
      })
      .catch(error => {
        if (refreshId === dashboardRefreshId) {
          rulesTableBody.innerHTML = '<tr><td colspan="5">Association rules could not be loaded.</td></tr>';
        }
        console.error('Association rules failed to load', error);
      });

    await loadCustomerOptions();
  } catch (error) {
    console.error('Dashboard failed to load', error);
  }
}

function bindControls() {
  applyFiltersBtn.addEventListener('click', async () => {
    await refreshDashboard();
  });

  resetFiltersBtn.addEventListener('click', async () => {
    countryFilter.value = 'All';
    yearFilter.value = 'All';
    minSupportInput.value = 0.02;
    minConfidenceInput.value = 0.5;
    await refreshDashboard();
  });

  customerSelect.addEventListener('change', async (event) => {
    await loadCustomerAnalysis(event.target.value);
  });
}

async function init() {
  try {
    await loadFilterOptions();
    bindControls();
    await refreshDashboard();
  } catch (error) {
    console.error('Dashboard failed to load', error);
  }
}

init();
