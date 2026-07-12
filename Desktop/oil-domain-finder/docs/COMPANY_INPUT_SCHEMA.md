# Company Input Schema

Use UTF-8 CSV files with a header row. The importer accepts the following
columns:

| Column | Required | Meaning |
| --- | --- | --- |
| `company_name` | Yes | Company name. Blank values are rejected and recorded in SQLite's `import_errors` table. |
| `location` | No | Jurisdiction, country, or other disambiguating location. It is part of the deduplication key. |
| `website` | No | Existing known company website. Supply either a domain or an `http(s)` URL; the importer stores its scheme and hostname only. |

Additional columns are ignored so a permitted public dataset can be supplied
without pre-stripping it.

Example:

```csv
company_name,location,website
Example Oil Ltd,GB,example-oil.test
Harbor Gas Services,US,
```

The importer canonicalizes case and whitespace for the `(company_name,
location)` key. It stores every import as a run in local SQLite, creates one
checkpoint record per unique company per run, and commits bounded batches. It
does not perform web lookups or treat a supplied website as independently
verified.
