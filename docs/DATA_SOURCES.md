# Data Sources

## Refugee Processing Center

**Publisher:** U.S. Department of State, Refugee Processing Center

**Current reports:**  
https://www.rpc.state.gov/admissions-and-arrivals/

**Historical reports:**  
https://www.rpc.state.gov/archives/

The Refugee Processing Center publishes current fiscal-year reports and historical refugee-arrival reports. The historical archive includes **Refugee Arrivals by State and Nationality** reports for FY2012 onward. These reports provide arrivals by state of resettlement, primary applicant nationality, and month of admission.

Current-year reports are periodically reconciled, so historical values may change after initial publication. The ingestion pipeline should therefore preserve retrieval dates and source snapshots rather than assuming previously downloaded reports are immutable.

### Planned use

The first forecasting dataset will aggregate the source reports to:

```text
state × calendar month
```

Planned fields include:

- state
- calendar year
- calendar month
- fiscal year
- monthly refugee arrivals
- source report
- source retrieval date

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
