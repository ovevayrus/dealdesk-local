import type { Economics } from "@dealdesk/contracts";

// Pricing-service strings reach the browser as markup, so escape every interpolation.
function esc(value: string | number): string {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function renderEconomicsFragment(
  economics: Economics,
  quoteId: string,
  version: number,
  scenario: "base" | "shock" = "base"
): string {
  const isShock = scenario === "shock";
  // Red on an explicit block warning or on a floor breach, so a low margin
  // cannot render green just because the service emitted no warning.
  const breachesFloor = Number(economics.stressMargin) < Number(economics.marginFloor);
  const isBlock = economics.warnings.some((w) => w.severity === "block") || breachesFloor;

  const warningsHtml =
    economics.warnings.length > 0
      ? `<div class="warnings-container">
          ${economics.warnings
            .map(
              (w) => `
            <div class="warning-box ${esc(w.severity)}">
              <strong>[${esc(w.severity.toUpperCase())}] ${esc(w.code)}:</strong> ${esc(w.message)}
            </div>`
            )
            .join("")}
        </div>`
      : "";

  const costsRows = economics.costs
    .map(
      (c) => `
      <tr>
        <td>${esc(c.label)}</td>
        <td class="numeric">$${esc(c.expected)}</td>
        <td class="numeric">$${esc(c.stress)}</td>
      </tr>`
    )
    .join("");

  return `
    <h2>Economics & Sensitivity (v${esc(version)})</h2>

    ${warningsHtml}

    <div class="sensitivity-controls" style="background: #f1f5f9; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; display: flex; gap: 1rem; align-items: flex-end;">
      <div style="flex: 1;">
        <label for="scenario-select" style="display: block; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.25rem;">
          Scenario:
        </label>
        <select id="scenario-select" style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 4px; font-size: 0.85rem;">
          <option value="base" ${!isShock ? "selected" : ""}>Base Case</option>
          <option value="shock" ${isShock ? "selected" : ""}>Supplier Shock (+8% cost)</option>
        </select>
      </div>
      <div style="flex: 1;">
        <label for="supplier-delta-input" style="display: block; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.25rem;">
          Supplier Cost Delta (%):
        </label>
        <input
          type="number"
          id="supplier-delta-input"
          step="0.5"
          min="-20"
          max="20"
          value="0.00"
          style="width: 100%; padding: 0.4rem; border: 1px solid var(--border-color); border-radius: 4px; font-size: 0.85rem;"
        />
      </div>
      <div>
        <button id="reprice-btn" type="button" style="padding: 0.45rem 0.85rem; background: var(--primary); color: white; border: none; border-radius: 4px; font-weight: 600; font-size: 0.85rem; cursor: pointer;">
          Reprice Deal
        </button>
      </div>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>Cost Item</th>
          <th class="numeric">Expected (${esc(economics.currency)})</th>
          <th class="numeric">Stress (${esc(economics.currency)})</th>
        </tr>
      </thead>
      <tbody>
        ${costsRows}
        <tr style="font-weight: 600; border-top: 2px solid var(--border-color);">
          <td>Total Cost Basis</td>
          <td class="numeric">$${esc(economics.baseCostTotal)}</td>
          <td class="numeric">$${esc(economics.stressCostTotal)}</td>
        </tr>
      </tbody>
    </table>

    <table class="data-table">
      <tbody>
        <tr>
          <td>Gross Margin (Base Case)</td>
          <td class="numeric"><strong>${esc(economics.grossMargin)}%</strong></td>
        </tr>
        <tr>
          <td>Stress Margin</td>
          <td class="numeric">
            <strong style="color: ${isBlock ? "var(--danger)" : "var(--success)"};">
              ${esc(economics.stressMargin)}%
            </strong>
          </td>
        </tr>
        <tr>
          <td>Policy Margin Floor</td>
          <td class="numeric">${esc(economics.marginFloor)}%</td>
        </tr>
        <tr>
          <td>Min Acceptable Price</td>
          <td class="numeric">$${esc(economics.minAcceptablePrice)}</td>
        </tr>
        <tr>
          <td>Recommended Price</td>
          <td class="numeric">$${esc(economics.recommendedPrice)}</td>
        </tr>
        <tr>
          <td>Feasible Range</td>
          <td class="numeric">${esc(economics.feasibleRange.low)} – ${esc(economics.feasibleRange.high)}</td>
        </tr>
        <tr>
          <td>Data Feed Version</td>
          <td class="numeric"><code>${esc(economics.dataVersion)}</code></td>
        </tr>
      </tbody>
    </table>
  `;
}
