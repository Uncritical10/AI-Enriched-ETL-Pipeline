select
    order_date,
    city,
    count(*)                                                   as orders,
    count_if(is_delivered)                                     as delivered_orders,
    round(coalesce(count_if(order_status = 'Cancelled') / nullif(count(*), 0), 0), 4) as cancel_rate,
    sum(case when is_delivered then sales_amount else 0 end)   as gmv,
    round(coalesce(
        sum(case when is_delivered then sales_amount else 0 end)
        / nullif(count_if(is_delivered), 0), 0), 2)            as aov
from {{ ref('fct_orders') }}
group by 1, 2
