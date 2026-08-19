| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax year shown on the Schedule K-1 (Form 1065)|2025|
|`TaxYearStartDate`|`date`|`extract`|Beginning date of the partnership tax year (if shown)|2025-01-01|
|`TaxYearEndDate`|`date`|`extract`|Ending date of the partnership tax year (if shown)|2025-12-31|
|`Partnership`|`object`|`generate`|Part I information about the partnership. (Schedule K-1 Form 1065)||
|`Partnership.EIN`|`string`|`extract`|Partnership employer identification number (EIN)|12-3456789|
|`Partnership.Name`|`string`|`extract`|Partnership name as printed|Northwind Partners LP|
|`Partnership.Address`|`string`|`extract`|Partnership mailing address|123 Main St, Seattle, WA 98101|
|`Partnership.IRSCenterFiledReturn`|`string`|`extract`|IRS center (e.g., city/state) where partnership filed return (if shown)|Ogden, UT|
|`Partnership.IsPubliclyTradedPartnership`|`boolean`|`extract`|Indicator that the partnership is publicly traded (as marked)|false|
|`Partner`|`object`|`generate`|Part II information about the partner. (Schedule K-1 Form 1065)||
|`Partner.SSNOrTIN`|`string`|`extract`|Partner identifying number (SSN/ITIN/EIN) as printed|123-45-6789|
|`Partner.Name`|`string`|`extract`|Partner name as printed|Jordan Taylor|
|`Partner.Address`|`string`|`extract`|Partner mailing address|789 Oak Ave, San Jose, CA 95112|
|`Partner.Type`|`array`|`generate`|Partner type checkbox selection. This field can have one or more of the following values: 'GeneralPartnerOrLLCMemberManager', 'LimitedPartnerOrOtherLLCMember'||
|`Partner.Type.*`|`string`|`extract`||GeneralPartnerOrLLCMemberManager|
|`Partner.ResidencyStatus`|`array`|`generate`|Partner residency checkbox selection. This field can have one or more of the following values: 'DomesticPartner', 'ForeignPartner'||
|`Partner.ResidencyStatus.*`|`string`|`extract`||DomesticPartner|
|`Partner.IsDisregardedEntity`|`boolean`|`extract`|Indicator that the partner is a disregarded entity (as marked)|false|
|`Partner.DisregardedEntityTIN`|`string`|`extract`|Taxpayer identification number (TIN) for the disregarded entity (if provided)|98-7654321|
|`Partner.DisregardedEntityName`|`string`|`extract`|Name of the disregarded entity (if provided)|JT Holdings LLC|
|`Partner.EntityType`|`string`|`extract`|Partner type/entity classification as printed (e.g., Individual, LLC, Corporation)|Individual|
|`Partner.IsRetirementPlan`|`boolean`|`extract`|Indicator that the partner is a retirement plan (as marked)|false|
|`Partner.BeginningProfitPercentage`|`number`|`extract`|Partner's beginning-of-year profit sharing percentage (0-100)|25|
|`Partner.EndingProfitPercentage`|`number`|`extract`|Partner's end-of-year profit sharing percentage (0-100)|30|
|`Partner.BeginningLossPercentage`|`number`|`extract`|Partner's beginning-of-year loss sharing percentage (0-100)|25|
|`Partner.EndingLossPercentage`|`number`|`extract`|Partner's end-of-year loss sharing percentage (0-100)|30|
|`Partner.BeginningCapitalPercentage`|`number`|`extract`|Partner's beginning-of-year capital ownership percentage (0-100)|25|
|`Partner.EndingCapitalPercentage`|`number`|`extract`|Partner's end-of-year capital ownership percentage (0-100)|30|
|`Partner.DecreaseReason`|`array`|`generate`|Reason for any ownership decrease checkbox selection. This field can have one or more of the following values: 'Sale', 'ExchangeOfPartnershipInterest'||
|`Partner.DecreaseReason.*`|`string`|`extract`||Sale|
|`Partner.BeginningNonrecourseLiability`|`number`|`extract`|Partner's share of nonrecourse liabilities at beginning of year (if shown)|15000|
|`Partner.EndingNonrecourseLiability`|`number`|`extract`|Partner's share of nonrecourse liabilities at end of year (if shown)|12000|
|`Partner.BeginningQualifiedNonrecourseFinancingLiability`|`number`|`extract`|Partner's share of qualified nonrecourse financing at beginning of year (if shown)|8000|
|`Partner.EndingQualifiedNonrecourseFinancingLiability`|`number`|`extract`|Partner's share of qualified nonrecourse financing at end of year (if shown)|7500|
|`Partner.BeginningRecourseLiability`|`number`|`extract`|Partner's share of recourse liabilities at beginning of year (if shown)|2000|
|`Partner.EndingRecourseLiability`|`number`|`extract`|Partner's share of recourse liabilities at end of year (if shown)|1800|
|`Partner.IsLiabilityFromLowerTierPartnershipIncluded`|`boolean`|`extract`|Indicator that liability amounts include amounts from lower-tier partnerships (as marked)|false|
|`Partner.IsSubjectToGuaranteesOrPaymentObligations`|`boolean`|`extract`|Indicator that the partner is subject to guarantees or other payment obligations (as marked)|false|
|`Partner.BeginningCapitalAccount`|`number`|`extract`|Beginning capital account balance (tax basis) as shown|50000|
|`Partner.CapitalContributed`|`number`|`extract`|Capital contributed during the year, as shown|10000|
|`Partner.CurrentYearNetIncomeOrLoss`|`number`|`extract`|Current year net income (loss) affecting the capital account, as shown|7500|
|`Partner.OtherIncreaseOrDecrease`|`number`|`extract`|Other increases (decreases) affecting the capital account, as shown|-250|
|`Partner.WithdrawalsAndDistributions`|`number`|`extract`|Withdrawals and distributions affecting the capital account, as shown|1200|
|`Partner.EndingCapitalAccount`|`number`|`extract`|Ending capital account balance (tax basis) as shown|66050|
|`Partner.ContributedPropertyWithBuiltInGainOrLoss`|`array`|`generate`|Answer to 'Did the partner contribute property with a built-in gain (loss)?' checkbox selection. This field can have one or more of the following values: 'Yes', 'No'||
|`Partner.ContributedPropertyWithBuiltInGainOrLoss.*`|`string`|`extract`||No|
|`Partner.BeginningNetUnrecognizedSection704CGainOrLoss`|`number`|`extract`|Beginning-of-year net unrecognized section 704(c) gain (loss), as shown|0|
|`Partner.EndingNetUnrecognizedSection704CGainOrLoss`|`number`|`extract`|End-of-year net unrecognized section 704(c) gain (loss), as shown|2500|
|`IsFinalK1`|`boolean`|`extract`|Indicator that this K-1 is marked as final|false|
|`IsAmendedK1`|`boolean`|`extract`|Indicator that this K-1 is marked as amended|false|
|`PartnerShare`|`object`|`generate`|Part III information about the partner's share of current year income, deductions, credits, and other items (Schedule K-1 Form 1065)||
|`PartnerShare.OrdinaryBusinessIncomeOrLoss`|`number`|`extract`|Ordinary business income (loss) allocated to the partner|25000|
|`PartnerShare.NetRentalRealEstateIncomeOrLoss`|`number`|`extract`|Net rental real estate income (loss) allocated to the partner|-500|
|`PartnerShare.OtherNetRentalIncomeOrLoss`|`number`|`extract`|Other net rental income (loss) allocated to the partner|125|
|`PartnerShare.GuaranteedPaymentsForServices`|`number`|`extract`|Guaranteed payments for services|8000|
|`PartnerShare.GuaranteedPaymentsForCapital`|`number`|`extract`|Guaranteed payments for capital|1200|
|`PartnerShare.TotalGuaranteedPayments`|`number`|`extract`|Total guaranteed payments|9200|
|`PartnerShare.InterestIncome`|`number`|`extract`|Interest income allocated to the partner|850.25|
|`PartnerShare.OrdinaryDividends`|`number`|`extract`|Ordinary dividends allocated to the partner|1200|
|`PartnerShare.QualifiedDividends`|`number`|`extract`|Qualified dividends included in ordinary dividends (if reported)|900|
|`PartnerShare.DividendEquivalents`|`number`|`extract`|Dividend equivalents, if separately reported|0|
|`PartnerShare.Royalties`|`number`|`extract`|Royalties allocated to the partner|75|
|`PartnerShare.NetShortTermCapitalGainOrLoss`|`number`|`extract`|Net short-term capital gain (loss) allocated to the partner|250|
|`PartnerShare.NetLongTermCapitalGainOrLoss`|`number`|`extract`|Net long-term capital gain (loss) allocated to the partner|1750|
|`PartnerShare.Collectibles28PercentGainOrLoss`|`number`|`extract`|Collectibles (28%) gain (loss) amount, if separately stated|0|
|`PartnerShare.UnrecapturedSection1250Gain`|`number`|`extract`|Unrecaptured section 1250 gain amount, if separately stated|420|
|`PartnerShare.NetSection1231GainOrLoss`|`number`|`extract`|Net section 1231 gain (loss) amount, if separately stated|600|
|`PartnerShare.OtherIncomeOrLossItems`|`array`|`generate`|Other income (loss) items reported with a code and amount||
|`PartnerShare.OtherIncomeOrLossItems.*`|`object`|`generate`|||
|`PartnerShare.OtherIncomeOrLossItems.*.Code`|`string`|`extract`|Code shown for the other income (loss) item|A|
|`PartnerShare.OtherIncomeOrLossItems.*.Amount`|`number`|`extract`|Amount associated with the other income (loss) code|500|
|`PartnerShare.OtherIncomeOrLossItems.*.StatementReference`|`string`|`extract`|Statement reference for the other income (loss) item|STMT|
|`PartnerShare.Section179Deduction`|`number`|`extract`|Section 179 deduction allocated to the partner|1500|
|`PartnerShare.OtherDeductionItems`|`array`|`generate`|Other deduction items reported with a code and amount||
|`PartnerShare.OtherDeductionItems.*`|`object`|`generate`|||
|`PartnerShare.OtherDeductionItems.*.Code`|`string`|`extract`|Code shown for the other deduction item|A|
|`PartnerShare.OtherDeductionItems.*.Amount`|`number`|`extract`|Amount associated with the other deduction code|250|
|`PartnerShare.OtherDeductionItems.*.StatementReference`|`string`|`extract`|Statement reference for the other deduction item|STMT|
|`PartnerShare.SelfEmploymentEarningsOrLossItems`|`array`|`generate`|Self-employment earnings (loss) items reported with a code and amount||
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*`|`object`|`generate`|||
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*.Code`|`string`|`extract`|Code shown for the self-employment earnings (loss) item|A|
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*.Amount`|`number`|`extract`|Self-employment earnings (loss) amount associated with the code|25000|
|`PartnerShare.SelfEmploymentEarningsOrLossItems.*.StatementReference`|`string`|`extract`|Statement reference for the self-employment earnings (loss) item|STMT|
|`PartnerShare.CreditItems`|`array`|`generate`|Credit items reported with a code and amount||
|`PartnerShare.CreditItems.*`|`object`|`generate`|||
|`PartnerShare.CreditItems.*.Code`|`string`|`extract`|Code shown for the credit item|A|
|`PartnerShare.CreditItems.*.Amount`|`number`|`extract`|Amount associated with the credit code|100|
|`PartnerShare.CreditItems.*.StatementReference`|`string`|`extract`|Statement reference for the credit item|STMT|
|`PartnerShare.IsScheduleK3Attached`|`boolean`|`extract`|Indicator that Schedule K-3 is attached (if shown)|false|
|`PartnerShare.AlternativeMinimumTaxItems`|`array`|`generate`|Alternative minimum tax (AMT) items reported with a code and amount||
|`PartnerShare.AlternativeMinimumTaxItems.*`|`object`|`generate`|||
|`PartnerShare.AlternativeMinimumTaxItems.*.Code`|`string`|`extract`|Code shown for the AMT item|A|
|`PartnerShare.AlternativeMinimumTaxItems.*.Amount`|`number`|`extract`|Amount associated with the AMT item code|75|
|`PartnerShare.AlternativeMinimumTaxItems.*.StatementReference`|`string`|`extract`|Statement reference for the AMT item|STMT|
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems`|`array`|`generate`|Tax-exempt income and nondeductible expense items reported with a code and amount||
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*`|`object`|`generate`|||
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*.Code`|`string`|`extract`|Code shown for the tax-exempt/nondeductible item|A|
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*.Amount`|`number`|`extract`|Amount associated with the tax-exempt/nondeductible item code|42|
|`PartnerShare.TaxExemptIncomeAndNondeductibleExpenseItems.*.StatementReference`|`string`|`extract`|Statement reference for the tax-exempt/nondeductible item|STMT|
|`PartnerShare.DistributionItems`|`array`|`generate`|Distribution items reported with a code and amount||
|`PartnerShare.DistributionItems.*`|`object`|`generate`|||
|`PartnerShare.DistributionItems.*.Code`|`string`|`extract`|Code shown for the distribution item|A|
|`PartnerShare.DistributionItems.*.Amount`|`number`|`extract`|Amount associated with the distribution code|1200|
|`PartnerShare.DistributionItems.*.StatementReference`|`string`|`extract`|Statement reference for the distribution item|STMT|
|`PartnerShare.OtherInformationItems`|`array`|`generate`|Other information items reported with a code and amount/value||
|`PartnerShare.OtherInformationItems.*`|`object`|`generate`|||
|`PartnerShare.OtherInformationItems.*.Code`|`string`|`extract`|Code shown for the other information item|A|
|`PartnerShare.OtherInformationItems.*.Amount`|`number`|`extract`|Amount/value associated with the other information item code|250|
|`PartnerShare.OtherInformationItems.*.StatementReference`|`string`|`extract`|Statement reference for the other information item|STMT|
|`PartnerShare.ForeignTaxesPaidOrAccrued`|`number`|`extract`|Foreign taxes paid or accrued, if separately reported|1200|
|`PartnerShare.HasMoreThanOneActivityForAtRiskPurposes`|`boolean`|`extract`|Indicator that there is more than one activity for at-risk purposes|false|
|`PartnerShare.HasMoreThanOneActivityForPassiveActivityPurposes`|`boolean`|`extract`|Indicator that there is more than one activity for passive activity purposes|false|
