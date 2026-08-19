| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax year shown on the Schedule K-1 (Form 8865)|2025|
|`TaxYearStartDate`|`date`|`extract`|Beginning date of the foreign partnership tax year (if shown)|2025-01-01|
|`TaxYearEndDate`|`date`|`extract`|Ending date of the foreign partnership tax year (if shown)|2025-12-31|
|`Partnership`|`object`|`generate`|Part I information about the foreign partnership (Schedule K-1 Form 8865)||
|`Partnership.EIN`|`string`|`extract`|Foreign partnership identifying number shown (EIN, if provided)|98-7654321|
|`Partnership.ReferenceIdNumber`|`string`|`extract`|Reference ID number (if shown) used to identify the foreign partnership K-1|FP-2025-000123|
|`Partnership.Name`|`string`|`extract`|Foreign partnership name as printed|Fabrikam International Partners|
|`Partnership.Address`|`string`|`extract`|Foreign partnership mailing address|10 Rue de Rivoli, Paris, FR 75001|
|`Partner`|`object`|`generate`|Part II information about the partner (Schedule K-1 Form 8865)||
|`Partner.SSNOrTIN`|`string`|`extract`|U.S. partner identifying number (SSN/ITIN/EIN) as printed|123-45-6789|
|`Partner.Name`|`string`|`extract`|U.S. partner name as printed|Avery Chen|
|`Partner.Address`|`string`|`extract`|U.S. partner mailing address|456 Pine St, Austin, TX 78701|
|`Partner.IsDisregardedEntity`|`boolean`|`extract`|Indicator that the partner is a disregarded entity (as marked)|false|
|`Partner.DisregardedEntityTIN`|`string`|`extract`|Taxpayer identification number (TIN) for the disregarded entity (if provided)|98-7654321|
|`Partner.DisregardedEntityName`|`string`|`extract`|Name of the disregarded entity (if provided)|AC Holdings LLC|
|`Partner.BeginningProfitPercentage`|`number`|`extract`|Partner's beginning-of-year profit sharing percentage (0-100)|10|
|`Partner.EndingProfitPercentage`|`number`|`extract`|Partner's end-of-year profit sharing percentage (0-100)|12.5|
|`Partner.BeginningLossPercentage`|`number`|`extract`|Partner's beginning-of-year loss sharing percentage (0-100)|10|
|`Partner.EndingLossPercentage`|`number`|`extract`|Partner's end-of-year loss sharing percentage (0-100)|12.5|
|`Partner.BeginningCapitalPercentage`|`number`|`extract`|Partner's beginning-of-year capital ownership percentage (0-100)|10|
|`Partner.EndingCapitalPercentage`|`number`|`extract`|Partner's end-of-year capital ownership percentage (0-100)|12.5|
|`Partner.BeginningDeductionsPercentage`|`number`|`extract`|Partner's beginning-of-year deduction sharing percentage (0-100), if shown|10|
|`Partner.EndingDeductionsPercentage`|`number`|`extract`|Partner's end-of-year deduction sharing percentage (0-100), if shown|12.5|
|`Partner.DecreaseReason`|`array`|`generate`|If the partner's share percentage(s) decreased, indicates whether the decrease is due to a sale or an exchange of the partnership interest (checkbox). This field can have one or more of the following values: 'Sale', 'ExchangeOfPartnershipInterest'||
|`Partner.DecreaseReason.*`|`string`|`extract`||Sale|
|`Partner.BeginningCapitalAccount`|`number`|`extract`|Beginning capital account balance (tax basis) as shown|15000|
|`Partner.CapitalContributed`|`number`|`extract`|Capital contributed during the year, as shown|2000|
|`Partner.CurrentYearNetIncomeOrLoss`|`number`|`extract`|Current year net income (loss) affecting the capital account, as shown|1250|
|`Partner.OtherIncreaseOrDecrease`|`number`|`extract`|Other increases (decreases) affecting the capital account, as shown|-50|
|`Partner.WithdrawalsAndDistributions`|`number`|`extract`|Withdrawals and distributions affecting the capital account, as shown|500|
|`Partner.EndingCapitalAccount`|`number`|`extract`|Ending capital account balance (tax basis) as shown|17700|
|`Partner.BeginningNetUnrecognizedSection704CGainOrLoss`|`number`|`extract`|Beginning-of-year net unrecognized section 704(c) gain (loss), as shown|0|
|`Partner.EndingNetUnrecognizedSection704CGainOrLoss`|`number`|`extract`|End-of-year net unrecognized section 704(c) gain (loss), as shown|500|
|`IsFinalK1`|`boolean`|`extract`|Indicator that this K-1 is marked as final|false|
|`IsAmendedK1`|`boolean`|`extract`|Indicator that this K-1 is marked as amended|false|
|`PartnerShare`|`object`|`generate`|Part III information about the partner's share of income, deductions, credits, and other items. (Schedule K-1 Form 8865)||
|`PartnerShare.OrdinaryBusinessIncomeOrLoss`|`number`|`extract`|Ordinary business income (loss) allocated to the partner|5000|
|`PartnerShare.NetRentalRealEstateIncomeOrLoss`|`number`|`extract`|Net rental real estate income (loss) allocated to the partner|-150|
|`PartnerShare.OtherNetRentalIncomeOrLoss`|`number`|`extract`|Other net rental income (loss) allocated to the partner|45|
|`PartnerShare.GuaranteedPaymentsForServices`|`number`|`extract`|Guaranteed payments for services|1200|
|`PartnerShare.GuaranteedPaymentsForCapital`|`number`|`extract`|Guaranteed payments for capital|150|
|`PartnerShare.TotalGuaranteedPayments`|`number`|`extract`|Total guaranteed payments|1350|
|`PartnerShare.InterestIncome`|`number`|`extract`|Interest income allocated to the partner|85.5|
|`PartnerShare.OrdinaryDividends`|`number`|`extract`|Ordinary dividends allocated to the partner|120|
|`PartnerShare.QualifiedDividends`|`number`|`extract`|Qualified dividends included in ordinary dividends (if reported)|90|
|`PartnerShare.DividendEquivalents`|`number`|`extract`|Dividend equivalents, if separately reported|0|
|`PartnerShare.Royalties`|`number`|`extract`|Royalties allocated to the partner|10|
|`PartnerShare.NetShortTermCapitalGainOrLoss`|`number`|`extract`|Net short-term capital gain (loss) allocated to the partner|25|
|`PartnerShare.NetLongTermCapitalGainOrLoss`|`number`|`extract`|Net long-term capital gain (loss) allocated to the partner|175|
|`PartnerShare.Collectibles28PercentGainOrLoss`|`number`|`extract`|Collectibles (28%) gain (loss) amount, if separately stated|0|
|`PartnerShare.UnrecapturedSection1250Gain`|`number`|`extract`|Unrecaptured section 1250 gain amount, if separately stated|40|
|`PartnerShare.NetSection1231GainOrLoss`|`number`|`extract`|Net section 1231 gain (loss) amount, if separately stated|60|
|`PartnerShare.OtherIncomeOrLossItems`|`array`|`generate`|Other income (loss) items reported with a code and amount||
|`PartnerShare.OtherIncomeOrLossItems.*`|`object`|`generate`|||
|`PartnerShare.OtherIncomeOrLossItems.*.Code`|`string`|`extract`|Code shown for the other income (loss) item|A|
|`PartnerShare.OtherIncomeOrLossItems.*.Amount`|`number`|`extract`|Amount associated with the other income (loss) code|350|
|`PartnerShare.OtherIncomeOrLossItems.*.StatementReference`|`string`|`extract`|Statement reference for the other income (loss) item|STMT|
|`PartnerShare.Section179Deduction`|`number`|`extract`|Section 179 deduction allocated to the partner|50|
|`PartnerShare.OtherDeductionItems`|`array`|`generate`|Other deduction items reported with a code and amount||
|`PartnerShare.OtherDeductionItems.*`|`object`|`generate`|||
|`PartnerShare.OtherDeductionItems.*.Code`|`string`|`extract`|Code shown for the other deduction item|A|
|`PartnerShare.OtherDeductionItems.*.Amount`|`number`|`extract`|Amount associated with the other deduction code|125|
|`PartnerShare.OtherDeductionItems.*.StatementReference`|`string`|`extract`|Statement reference for the other deduction item|STMT|
|`PartnerShare.SelfEmploymentEarningsOrLossItems`|`array`|`generate`|Self-employment earnings (loss) items reported with a code and amount||
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*`|`object`|`generate`|||
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*.Code`|`string`|`extract`|Code shown for the self-employment earnings (loss) item|A|
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*.Amount`|`number`|`extract`|Self-employment earnings (loss) amount associated with the code|5000|
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*.StatementReference`|`string`|`extract`|Statement reference for the self-employment earnings (loss) item|STMT|
|`PartnerShare.CreditItems`|`array`|`generate`|Credit items reported with a code and amount||
|`PartnerShare.CreditItems.*`|`object`|`generate`|||
|`PartnerShare.CreditItems.*.Code`|`string`|`extract`|Code shown for the credit item|A|
|`PartnerShare.CreditItems.*.Amount`|`number`|`extract`|Amount associated with the credit code|60|
|`PartnerShare.CreditItems.*.StatementReference`|`string`|`extract`|Statement reference for the credit item|STMT|
|`PartnerShare.IsScheduleK3Attached`|`boolean`|`extract`|Indicator that Schedule K-3 is attached (if shown)|true|
|`PartnerShare.AlternativeMinimumTaxItems`|`array`|`generate`|Alternative minimum tax (AMT) items reported with a code and amount||
|`PartnerShare.AlternativeMinimumTaxItems.*`|`object`|`generate`|||
|`PartnerShare.AlternativeMinimumTaxItems.*.Code`|`string`|`extract`|Code shown for the AMT item|A|
|`PartnerShare.AlternativeMinimumTaxItems.*.Amount`|`number`|`extract`|Amount associated with the AMT item code|25|
|`PartnerShare.AlternativeMinimumTaxItems.*.StatementReference`|`string`|`extract`|Statement reference for the AMT item|STMT|
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems`|`array`|`generate`|Tax-exempt income and nondeductible expense items reported with a code and amount||
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*`|`object`|`generate`|||
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*.Code`|`string`|`extract`|Code shown for the tax-exempt/nondeductible item|A|
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*.Amount`|`number`|`extract`|Amount associated with the tax-exempt/nondeductible item code|15|
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*.StatementReference`|`string`|`extract`|Statement reference for the tax-exempt/nondeductible item|STMT|
|`PartnerShare.DistributionItems`|`array`|`generate`|Distribution items reported with a code and amount||
|`PartnerShare.DistributionItems.*`|`object`|`generate`|||
|`PartnerShare.DistributionItems.*.Code`|`string`|`extract`|Code shown for the distribution item|A|
|`PartnerShare.DistributionItems.*.Amount`|`number`|`extract`|Amount associated with the distribution code|500|
|`PartnerShare.DistributionItems.*.StatementReference`|`string`|`extract`|Statement reference for the distribution item|STMT|
|`PartnerShare.OtherInformationItems`|`array`|`generate`|Other information items reported with a code and amount/value||
|`PartnerShare.OtherInformationItems.*`|`object`|`generate`|||
|`PartnerShare.OtherInformationItems.*.Code`|`string`|`extract`|Code shown for the other information item|A|
|`PartnerShare.OtherInformationItems.*.Amount`|`number`|`extract`|Amount/value associated with the other information item code|100|
|`PartnerShare.OtherInformationItems.*.StatementReference`|`string`|`extract`|Statement reference for the other information item|STMT|
|`PartnerShare.ForeignTaxesPaidOrAccrued`|`number`|`extract`|Foreign taxes paid or accrued, if separately reported|300|
