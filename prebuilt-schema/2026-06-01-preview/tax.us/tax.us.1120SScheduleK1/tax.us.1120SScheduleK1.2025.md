| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax year shown on the Schedule K-1 (Form 1120-S)|2025|
|`TaxYearStartDate`|`date`|`extract`|Beginning date of the corporation tax year (if shown)|2025-01-01|
|`TaxYearEndDate`|`date`|`extract`|Ending date of the corporation tax year (if shown)|2025-12-31|
|`Corporation`|`object`|`generate`|Part I information about the corporation (Schedule K-1 Form 1120-S)||
|`Corporation.EIN`|`string`|`extract`|Corporation employer identification number (EIN)|12-3456789|
|`Corporation.Name`|`string`|`extract`|Corporation name as printed|Contoso corporation|
|`Corporation.Address`|`string`|`extract`|Corporation mailing address|1 Microsoft Way, Redmond, WA 98052|
|`Corporation.IRSCenterFiledReturn`|`string`|`extract`|IRS center (e.g., city/state) where corporation filed return (if shown)|Ogden, UT|
|`Corporation.BeginningTotalShares`|`number`|`extract`|Total shares outstanding at the beginning of the tax year (if shown)|1000|
|`Corporation.EndingTotalShares`|`number`|`extract`|Total shares outstanding at the end of the tax year (if shown)|1000|
|`Shareholder`|`object`|`generate`|Part II information about the shareholder (Schedule K-1 Form 1120-S)||
|`Shareholder.IdentifyingNumber`|`string`|`extract`|Shareholder identifying number (SSN/ITIN/EIN) as printed|123-45-6789|
|`Shareholder.Name`|`string`|`extract`|Shareholder name as printed|Alex Morgan|
|`Shareholder.Address`|`string`|`extract`|Shareholder mailing address|789 Oak Ave, San Jose, CA 95112|
|`Shareholder.ResponsibleReportingEntityTIN`|`string`|`extract`|Taxpayer identification number (TIN) of the individual or entity responsible for reporting when the shareholder is a disregarded entity, trust, estate, nominee, or similar person (Part II line F2) (if provided)|98-7654321|
|`Shareholder.ResponsibleReportingEntityName`|`string`|`extract`|Name of the individual or entity responsible for reporting when the shareholder is a disregarded entity, trust, estate, nominee, or similar person (Part II line F2) (if provided)|JT Holdings LLC|
|`Shareholder.EntityType`|`string`|`extract`|Shareholder type/entity classification as printed (e.g., Individual, Estate, Trust, Corporation)|Individual|
|`Shareholder.CurrentYearAllocationPercentage`|`number`|`extract`|Shareholder's current-year percentage of ownership/allocation as shown (0-100)|12.5|
|`Shareholder.BeginningShares`|`number`|`extract`|Shareholder shares at beginning of tax year (if shown)|100|
|`Shareholder.EndingShares`|`number`|`extract`|Shareholder shares at end of tax year (if shown)|120|
|`Shareholder.BeginningLoanBalance`|`number`|`extract`|Loan balance from shareholder at beginning of tax year (if shown)|5000|
|`Shareholder.EndingLoanBalance`|`number`|`extract`|Loan balance from shareholder at end of tax year (if shown)|3500|
|`IsFinalK1`|`boolean`|`extract`|Indicator that this K-1 is marked as final|false|
|`IsAmendedK1`|`boolean`|`extract`|Indicator that this K-1 is marked as amended|false|
|`ShareholderShare`|`object`|`generate`|Part III information about the shareholder's share of income, deductions, credits, and other items. (Schedule K-1 Form 1120-S)||
|`ShareholderShare.OrdinaryBusinessIncomeOrLoss`|`number`|`extract`|Ordinary business income (loss) allocated to the shareholder|25000|
|`ShareholderShare.NetRentalRealEstateIncomeOrLoss`|`number`|`extract`|Net rental real estate income (loss) allocated to the shareholder|-500|
|`ShareholderShare.OtherNetRentalIncomeOrLoss`|`number`|`extract`|Other net rental income (loss) allocated to the shareholder|125|
|`ShareholderShare.InterestIncome`|`number`|`extract`|Interest income allocated to the shareholder|850.25|
|`ShareholderShare.OrdinaryDividends`|`number`|`extract`|Ordinary dividends allocated to the shareholder|1200|
|`ShareholderShare.QualifiedDividends`|`number`|`extract`|Qualified dividends included in ordinary dividends (if reported)|900|
|`ShareholderShare.Royalties`|`number`|`extract`|Royalties allocated to the shareholder|75|
|`ShareholderShare.NetShortTermCapitalGainOrLoss`|`number`|`extract`|Net short-term capital gain (loss) allocated to the shareholder|250|
|`ShareholderShare.NetLongTermCapitalGainOrLoss`|`number`|`extract`|Net long-term capital gain (loss) allocated to the shareholder|1750|
|`ShareholderShare.Collectibles28PercentGainOrLoss`|`number`|`extract`|Collectibles (28%) gain (loss) amount, if separately stated|0|
|`ShareholderShare.UnrecapturedSection1250Gain`|`number`|`extract`|Unrecaptured section 1250 gain amount, if separately stated|420|
|`ShareholderShare.NetSection1231GainOrLoss`|`number`|`extract`|Net section 1231 gain (loss) amount, if separately stated|600|
|`ShareholderShare.OtherIncomeOrLossItems`|`array`|`generate`|Other income (loss) items reported with a code and amount||
|`ShareholderShare.OtherIncomeOrLossItems.*`|`object`|`generate`|||
|`ShareholderShare.OtherIncomeOrLossItems.*.Code`|`string`|`extract`|Code shown for the other income (loss) item|A|
|`ShareholderShare.OtherIncomeOrLossItems.*.Amount`|`number`|`extract`|Amount associated with the other income (loss) code|500|
|`ShareholderShare.OtherIncomeOrLossItems.*.StatementReference`|`string`|`extract`|Statement reference for the other income (loss) item|STMT|
|`ShareholderShare.Section179Deduction`|`number`|`extract`|Section 179 deduction allocated to the shareholder|1500|
|`ShareholderShare.OtherDeductionItems`|`array`|`generate`|Other deductions reported with a code and amount||
|`ShareholderShare.OtherDeductionItems.*`|`object`|`generate`|||
|`ShareholderShare.OtherDeductionItems.*.Code`|`string`|`extract`|Code shown for the other deduction item|A|
|`ShareholderShare.OtherDeductionItems.*.Amount`|`number`|`extract`|Amount associated with the other deduction code|250|
|`ShareholderShare.OtherDeductionItems.*.StatementReference`|`string`|`extract`|Statement reference for the other deduction item|STMT|
|`ShareholderShare.CreditItems`|`array`|`generate`|Credit items reported with a code and amount||
|`ShareholderShare.CreditItems.*`|`object`|`generate`|||
|`ShareholderShare.CreditItems.*.Code`|`string`|`extract`|Code shown for the credit item|A|
|`ShareholderShare.CreditItems.*.Amount`|`number`|`extract`|Amount associated with the credit code|100|
|`ShareholderShare.CreditItems.*.StatementReference`|`string`|`extract`|Statement reference for the credit item|STMT|
|`ShareholderShare.IsScheduleK3Attached`|`boolean`|`extract`|Indicator that Schedule K-3 is attached (if shown)|false|
|`ShareholderShare.AlternativeMinimumTaxItems`|`array`|`generate`|Alternative minimum tax (AMT) items reported with a code and amount||
|`ShareholderShare.AlternativeMinimumTaxItems.*`|`object`|`generate`|||
|`ShareholderShare.AlternativeMinimumTaxItems.*.Code`|`string`|`extract`|Code shown for the AMT item|A|
|`ShareholderShare.AlternativeMinimumTaxItems.*.Amount`|`number`|`extract`|Amount associated with the AMT item code|75|
|`ShareholderShare.AlternativeMinimumTaxItems.*.StatementReference`|`string`|`extract`|Statement reference for the AMT item|STMT|
|`ShareholderShare.ItemsAffectingShareholderBasis`|`array`|`generate`|Items affecting shareholder basis reported with a code and amount||
|`ShareholderShare.ItemsAffectingShareholderBasis.*`|`object`|`generate`|||
|`ShareholderShare.ItemsAffectingShareholderBasis.*.Code`|`string`|`extract`|Code shown for the basis-affecting item|A|
|`ShareholderShare.ItemsAffectingShareholderBasis.*.Amount`|`number`|`extract`|Amount associated with the basis-affecting item code|1200|
|`ShareholderShare.ItemsAffectingShareholderBasis.*.StatementReference`|`string`|`extract`|Statement reference for the basis-affecting item|STMT|
|`ShareholderShare.OtherInformationItems`|`array`|`generate`|Other information items reported with a code and amount/value||
|`ShareholderShare.OtherInformationItems.*`|`object`|`generate`|||
|`ShareholderShare.OtherInformationItems.*.Code`|`string`|`extract`|Code shown for the other information item|A|
|`ShareholderShare.OtherInformationItems.*.Amount`|`number`|`extract`|Amount/value associated with the other information item code|42|
|`ShareholderShare.OtherInformationItems.*.StatementReference`|`string`|`extract`|Statement reference for the other information item|STMT|
|`ShareholderShare.HasMultipleAtRiskActivities`|`boolean`|`extract`|Indicator that there is more than one activity for at-risk purposes|false|
|`ShareholderShare.HasMultiplePassiveActivities`|`boolean`|`extract`|Indicator that there is more than one activity for passive activity purposes|false|
