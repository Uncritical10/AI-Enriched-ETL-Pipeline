select
    try_cast(id as bigint)                                                 as restaurant_id,
    name                                                                   as restaurant_name,
    trim(coalesce(nullif(regexp_extract(city, '[^,]+$'), ''), city))       as city,
    try_cast(nullif(rating, '--') as decimal(3,1))                         as rating,
    try_cast(nullif(regexp_extract(rating_count, '[0-9]+'), '') as bigint) as rating_count,
    try_cast(nullif(regexp_extract(cost, '[0-9]+'), '') as bigint)         as cost_for_two,
    cuisine,
    lic_no                                                                 as license_no
from {{ source('raw', 'restaurant') }}
where try_cast(id as bigint) is not null
