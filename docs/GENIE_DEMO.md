# Genie / AI/BI demo script — LW Commerce gold

Use after `lw_commerce_lakehouse` succeeds and gold tables exist in
`{catalog}.gold.*` (default catalog `workspace`).

In Databricks: **Genie** space over the four gold tables (or a SQL warehouse
AI/BI dashboard). Prefer asking in natural language; Genie will draft SQL.

## Gold tables to attach

| Table | Use for |
|-------|---------|
| `gold.gold_daily_revenue` | Time series, country mix, AOV |
| `gold.gold_top_products` | Product ranking, category mix |
| `gold.gold_order_fulfillment` | Status funnel / ops |
| `gold.gold_customer_orders` | Customer value, repeat buyers |

## Natural-language questions (EN / ES)

Ask Genie these in class (8–12). English first, then Spanish variant.

1. **EN:** What was total revenue by day in October 2026?  
   **ES:** ¿Cuál fue el revenue total por día en octubre 2026?

2. **EN:** Which country generated the most revenue?  
   **ES:** ¿Qué país generó más revenue?

3. **EN:** Show average order value by country, highest first.  
   **ES:** Mostrá el ticket promedio (AOV) por país, de mayor a menor.

4. **EN:** What are the top 10 products by revenue?  
   **ES:** ¿Cuáles son los 10 productos con más revenue?

5. **EN:** Which product category sold the most units?  
   **ES:** ¿Qué categoría de producto vendió más unidades?

6. **EN:** How many orders are in each fulfillment status for Argentina?  
   **ES:** ¿Cuántas órdenes hay en cada estado de fulfillment para Argentina?

7. **EN:** What share of orders are cancelled vs delivered overall?  
   **ES:** ¿Qué porcentaje de órdenes están canceladas vs entregadas en total?

8. **EN:** Who are the top 15 customers by lifetime revenue?  
   **ES:** ¿Quiénes son los 15 clientes con mayor revenue acumulado?

9. **EN:** How many customers placed more than 3 orders?  
   **ES:** ¿Cuántos clientes hicieron más de 3 órdenes?

10. **EN:** On which day did we have the most distinct customers?  
    **ES:** ¿En qué día tuvimos más clientes distintos?

11. **EN:** Compare revenue for electronics vs coffee products.  
    **ES:** Compará el revenue de productos electronics vs coffee.

12. **EN:** List customers whose primary country is NL and revenue over 500 EUR.  
    **ES:** Listá clientes con país principal NL y revenue mayor a 500 EUR.

### Stretch (if Genie joins across gold tables)

- **EN:** For the best-selling product, which countries buy it the most?  
  **ES:** Para el producto más vendido, ¿qué países lo compran más?
- **EN:** Is cancellation rate higher in BR than in MX?  
  **ES:** ¿La tasa de cancelación es más alta en BR que en MX?

## AI/BI dashboard tile ideas (3–4)

Build a simple Lakeview / AI/BI dashboard on the SQL warehouse:

1. **KPI row** — tiles from `gold_daily_revenue`:
   - Sum of `revenue_eur`
   - Sum of `orders`
   - Average of `avg_order_value_eur` (or weighted)
2. **Line chart** — `order_date` × `revenue_eur` (optionally color by `country`).
3. **Bar chart** — top 10 from `gold_top_products` (`product_name` × `revenue_eur`).
4. **Stacked bar or funnel** — `gold_order_fulfillment` (`status` × `order_count`, facet/filter by `country`).

Optional fifth tile: histogram or table of `gold_customer_orders.orders` to show repeat-purchase distribution.

## Classroom tips

- Re-run the DAG once so students see **append-only raw** + bronze **dedupe** (row counts: `just counts`).
- If Genie invents a column, point back to `docs` / `schema.yml` / `DESCRIBE TABLE`.
- Keep the PAT off the shared screen; use a teacher-owned Genie space.

## ES · Nota corta

Después del DAG, abrí Genie sobre las tablas `gold_*` y pedí las preguntas de arriba.
Los tiles del dashboard sirven para cerrar la demo en 5 minutos.
