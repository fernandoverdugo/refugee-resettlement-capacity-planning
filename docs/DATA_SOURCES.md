# Data Sources

## Refugee Processing Center

**Publisher:** U.S. Department of State, Refugee Processing Center

**Current reports:**  
https://www.rpc.state.gov/admissions-and-arrivals/

**Historical reports:**  
https://www.rpc.state.gov/archives/

The Refugee Processing Center publishes current fiscal-year reports and historical refugee-arrival reports. The historical archive includes **Refugee Arrivals by State and Nationality** reports for FY2012 onward.

A source audit identified an important format difference: archived FY2012–FY2020 Excel workbooks expose state-level fiscal-year totals, while FY2021 and later PDF reports provide usable monthly state detail. The project preserves that distinction rather than interpolating monthly values for the legacy years.

Current-year reports are periodically reconciled, so historical values may change after initial publication. The ingestion pipeline should therefore preserve retrieval dates and source snapshots rather than assuming previously downloaded reports are immutable.

### Planned use

The ingestion pipeline creates two normalized outputs:

```text
data/processed/rpc_state_fiscal_year.csv
data/processed/rpc_state_month.csv
```

The annual panel spans FY2012 onward. The monthly panel begins in FY2021, when the archived RPC source files provide month-level state detail.

Monthly-panel fields include:

- state
- calendar year
- calendar month
- fiscal year
- monthly refugee arrivals
- source report
- source URL
- source retrieval timestamp

Annual-panel fields include:

- state
- fiscal year
- annual refugee arrivals
- source report
- source URL
- source retrieval timestamp

Nationality will be retained in a more detailed normalized table where source structure permits.

## American Community Survey

**Publisher:** U.S. Census Bureau

**Developer documentation:**  
https://www.census.gov/data/developers/data-sets/acs-5year.html

**API base:**  
https://api.census.gov/data/

The ACS provides annual demographic, social, economic, and housing estimates. The capacity-planning layer will use state-level ACS indicators as contextual planning variables.

Initial candidate indicators:

- total population
- poverty rate
- unemployment rate
- median household income
- rental vacancy rate
- housing-cost burden
- foreign-born population
- limited-English-speaking households

### Interpretation

ACS measures will not be treated as causal determinants of refugee arrivals. They are intended to represent operational context for scenario analysis and resource planning.

## Data provenance requirements

Every normalized source should preserve, where applicable:

- source organization
- source URL
- source report or dataset vintage
- retrieval timestamp
- geographic grain
- temporal grain
- transformation version

Raw source files should never be silently overwritten without retaining enough metadata to reproduce the analytical dataset.
