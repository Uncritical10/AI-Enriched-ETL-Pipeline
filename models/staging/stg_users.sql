select
    try_cast(user_id as bigint)           as customer_id,
    name                                  as customer_name,
    email,
    try_cast("Age" as bigint)             as age,
    "Gender"                              as gender,
    "Marital Status"                      as marital_status,
    "Occupation"                          as occupation,
    "Monthly Income"                      as income_band,
    "Educational Qualifications"          as education,
    try_cast("Family size" as bigint)     as family_size
from {{ source('raw', 'users') }}
where try_cast(user_id as bigint) is not null
