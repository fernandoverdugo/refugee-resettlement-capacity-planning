# ACS Capacity Indicators

## Purpose

The ACS layer provides state-level context for resource-planning scenarios. These measures are not treated as causal determinants of refugee placement. They are operational context that can be combined with forecast demand and explicit planning assumptions.

## Dataset

The project uses the U.S. Census Bureau **American Community Survey 5-year Data Profiles** at state geography.

The Census Bureau currently requires an API key for data queries. Set:

```bash
export CENSUS_API_KEY="..."
```

before running:

```bash
python -m scripts.fetch_acs_capacity
```

The API key is never committed to the repository.

## Initial indicator set

| Project field | ACS variable | Interpretation |
| --- | --- | --- |
| population | DP05_0001E | total population |
| unemployment_rate | DP03_0009PE | civilian labor force unemployment rate |
| median_household_income | DP03_0062E | median household income |
| poverty_rate | DP03_0128PE | population below poverty level |
| rental_vacancy_rate | DP04_0005E | rental vacancy rate |
| median_gross_rent | DP04_0134E | median gross rent |
| rent_burden_35_plus_pct | DP04_0142PE | renters paying 35%+ of income toward gross rent |
| foreign_born_pct | DP02_0094PE | foreign-born share of population |

A derived `limited_english_pct` sums the ACS percentages for people age 5+ who speak English less than "very well" across Spanish, other Indo-European, Asian/Pacific Islander, and other-language categories.

## Interpretation principles

- Higher population does not automatically imply greater resettlement capacity.
- Higher income is not treated as an entitlement to additional arrivals.
- Foreign-born and language measures describe existing service context, not placement suitability.
- Housing, labor-market, and socioeconomic measures will enter scenario models through transparent weights or constraints.
- Optimization outputs will be presented as planning scenarios, not placement recommendations for individuals.

## Output

```text
data/processed/acs_state_capacity.csv
```

The panel is keyed by:

```text
state_fips × acs_year
```

and includes source dataset and source URL fields.
