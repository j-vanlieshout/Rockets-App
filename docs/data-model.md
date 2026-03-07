# Data Model

## Entities

### Team
| Field | Type | Notes |
|-------|------|-------|
| id | int | PK |
| name | string | Display name, e.g. "Unibet Rose Rockets" |
| slug | string | PCS slug prefix, e.g. "unibet-rose-rockets" |
| uci_code | string | 3-letter UCI code, e.g. "URR" |

### Rider
| Field | Type | Notes |
|-------|------|-------|
| id | int | PK |
| pcs_slug | string | e.g. "dylan-groenewegen" |
| full_name | string | |
| nationality | string | ISO 3-letter country code |
| date_of_birth | date | |
| age | int | |
| weight_kg | int | |
| height_cm | int | |
| specialty | string | PCS label, e.g. "Sprinter" |
| pcs_ranking | int | Current world ranking |
| pcs_points | int | Current season points |
| team_id | FK → Team | |

### Race
| Field | Type | Notes |
|-------|------|-------|
| id | int | PK |
| pcs_slug | string | e.g. "tour-de-france" |
| name | string | |
| season | int | Year |
| start_date | date | |
| end_date | date | |
| category | string | e.g. "2.UWT", "GT" |
| country | string | |

### RaceResult
| Field | Type | Notes |
|-------|------|-------|
| id | int | PK |
| race_id | FK → Race | |
| rider_id | FK → Rider | |
| team_id | FK → Team | |
| stage | string | "GC", "Stage 3", "Points", … |
| position | int | 1 = win |
| time_gap | string | e.g. "+0:45" |
| points | int | PCS points earned |

## PCS URL Patterns

| Resource | URL Pattern |
|----------|-------------|
| Team overview | `/team/{slug}-{year}/overview` |
| Team results | `/team/{slug}-{year}/results` |
| Rider profile | `/rider/{pcs-slug}` |
| Race overview | `/race/{pcs-slug}/{year}` |
| Race startlist | `/race/{pcs-slug}/{year}/startlist` |
