**Analyzer ID:** `prebuilt-healthInsuranceCard.us`

**Description:** US health insurance cards.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Insurer`|`string`|`extract`|Health insurance provider name|PREMERA<br>BLUE CROSS|
|`Member`|`object`|`generate`|Extracted member information||
|`Member.Name`|`string`|`extract`|Member name|ANGEL BROWN|
|`Member.BirthDate`|`date`|`extract`|Member birth date (ISO 8601 YYYY-MM-DD)|1958-01-06|
|`Member.Employer`|`string`|`extract`|Member employer|Microsoft|
|`Member.Sex`|`string`|`extract`|Member sex marker as printed on the card (e.g., M, F, X)|M|
|`Dependents`|`array`|`generate`|Array holding list of dependents, ordered where possible by membership suffix value||
|`Dependents.*`|`object`|`generate`|Extracted dependent information||
|`Dependents.*.Name`|`string`|`extract`|Dependent name|ALEX BROWN|
|`IdNumber`|`object`|`generate`|Extracted ID number information||
|`IdNumber.Prefix`|`string`|`extract`|Identification number prefix as it appears on some health insurance cards|ABC|
|`IdNumber.Number`|`string`|`extract`|Identification number|123456789|
|`IdNumber.Suffix`|`string`|`extract`|Identification number suffix as it appears on some health insurance cards|01|
|`GroupNumber`|`string`|`extract`|Insurance group number|1000000|
|`PrescriptionInformation`|`object`|`generate`|Extracted prescription information||
|`PrescriptionInformation.Issuer`|`string`|`extract`|ANSI issuer identification number (IIN)|(80840) 300-11908-77|
|`PrescriptionInformation.RxBIN`|`string`|`extract`|Prescription BIN number|987654|
|`PrescriptionInformation.RxPCN`|`string`|`extract`|Prescription processor control number|63200305|
|`PrescriptionInformation.RxGroupNumber`|`string`|`extract`|Prescription group number|BCAAXYZ|
|`PrescriptionInformation.RxId`|`string`|`extract`|Prescription identification number. If not present, will default to membership ID number|P97020065|
|`PrescriptionInformation.RxPlanNumber`|`string`|`extract`|Prescription plan number|A1|
|`PBM`|`string`|`extract`|Pharmacy Benefit Manager for the plan|CVS CAREMARK|
|`EffectiveDate`|`date`|`extract`|Date from which the plan is effective (ISO 8601 YYYY-MM-DD)|2012-08-12|
|`Copays`|`array`|`generate`|Array holding list of copay benefits||
|`Copays.*`|`object`|`generate`|Extracted copays information||
|`Copays.*.Benefit`|`string`|`extract`|Copay benefit name|Deductible|
|`Copays.*.Amount`|`number`|`extract`|Copay required amount|1500|
|`Payer`|`object`|`generate`|Extracted payer information||
|`Payer.Id`|`string`|`extract`|Payer ID number|89063|
|`Payer.Address`|`string`|`extract`|Payer address|123 Service St, Redmond WA, 98052|
|`Payer.PhoneNumber`|`string`|`extract`|Payer phone number|+1 (987) 213-5674|
|`Plan`|`object`|`generate`|Extracted plan information||
|`Plan.Number`|`string`|`extract`|Plan number|456|
|`Plan.Name`|`string`|`extract`|Plan name|HEALTH SAVINGS PLAN|
|`Plan.Type`|`string`|`extract`|Plan type|PPO|
|`MedicareMedicaidInformation`|`object`|`generate`|Extracted Medicare or Medicaid information||
|`MedicareMedicaidInformation.Id`|`string`|`extract`|Medicare or Medicaid number|1AB2-CD3-EF45|
|`MedicareMedicaidInformation.PartAEffectiveDate`|`date`|`extract`|Effective date of Medicare Part A (ISO 8601 YYYY-MM-DD)|2023-01-01|
|`MedicareMedicaidInformation.PartBEffectiveDate`|`date`|`extract`|Effective date of Medicare Part B (ISO 8601 YYYY-MM-DD)|2023-01-01|
