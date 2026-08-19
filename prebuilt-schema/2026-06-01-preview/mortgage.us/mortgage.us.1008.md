| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Borrower`|`object`|`generate`|Extracted borrower information||
|`Borrower.Name`|`string`|`extract`|Borrower's full name as written on the form|Stan Hettinger|
|`Borrower.NumberOfBorrowers`|`integer`|`extract`|Total number of borrowers|1|
|`Property`|`object`|`generate`|Extracted property information||
|`Property.Address`|`string`|`extract`|Property address|225 Bustleton Pike, Feasterville-Trevose, PA 19053|
|`Property.OccupancyStatus`|`array`|`generate`|Property occupancy status selection(s)||
|`Property.OccupancyStatus.*`|`string`|`extract`|||
|`Property.SalesPrice`|`number`|`extract`|Property sales price|800000|
|`Property.AppraisedValue`|`number`|`extract`|Property appraised value|800000|
|`Property.Type`|`array`|`generate`|Property type selection(s)||
|`Property.Type.*`|`string`|`extract`|||
|`Property.FreddieMacProjectClassificationType`|`array`|`generate`|Freddie Mac project classification selection(s)||
|`Property.FreddieMacProjectClassificationType.*`|`string`|`extract`|||
|`Property.FannieMaeProjectClassificationType`|`array`|`generate`|Fannie Mae project classification selection(s)||
|`Property.FannieMaeProjectClassificationType.*`|`string`|`extract`|||
|`Property.RightsType`|`array`|`generate`|Property rights selection(s)||
|`Property.RightsType.*`|`string`|`extract`|||
|`Mortgage`|`object`|`generate`|Extracted mortgage information||
|`Mortgage.LoanType`|`array`|`generate`|Mortgage loan type selection(s)||
|`Mortgage.LoanType.*`|`string`|`extract`|||
|`Mortgage.AmortizationType`|`array`|`generate`|Mortgage amortization type selection(s)||
|`Mortgage.AmortizationType.*`|`string`|`extract`|||
|`Mortgage.LoanPurposeType`|`array`|`generate`|Mortgage loan purpose selection(s)||
|`Mortgage.LoanPurposeType.*`|`string`|`extract`|||
|`Mortgage.LienPositionType`|`array`|`generate`|Mortgage lien position selection(s)||
|`Mortgage.LienPositionType.*`|`string`|`extract`|||
|`Mortgage.SubordinateFinancingAmount`|`number`|`extract`|Amount of subordinate financing|0|
|`Mortgage.LoanAmount`|`number`|`extract`|Loan amount|400000|
|`Mortgage.NoteRatePercentage`|`number`|`extract`|Note rate percentage|6.5000|
|`Mortgage.LoanTermInMonths`|`number`|`extract`|Loan term in months|240|
|`Mortgage.OriginatorType`|`array`|`generate`|Mortgage originator type selection(s)||
|`Mortgage.OriginatorType.*`|`string`|`extract`|||
|`Mortgage.BrokerOrCorrespondentName`|`string`|`extract`|Broker/Correspondent name|Mesh Nicki|
|`Mortgage.BrokerOrCorrespondentCompanyName`|`string`|`extract`|Broker/Correspondent company name||
|`Mortgage.TemporaryBuydownStatus`|`array`|`generate`|Temporary buydown status selection(s)||
|`Mortgage.TemporaryBuydownStatus.*`|`string`|`extract`|||
|`Mortgage.TemporaryBuydownTerms`|`string`|`extract`|Temporary buydown term details (if applicable)|36|
|`Underwriting`|`object`|`generate`|Extracted underwriting information||
|`Underwriting.UnderwriterName`|`string`|`extract`|Underwriter name|Abdiel Keeling|
|`Underwriting.AppraiserName`|`string`|`extract`|Appraiser name|Claudia Denesik|
|`Underwriting.AppraiserLicenseNumber`|`string`|`extract`|Appraiser license number|102896|
|`Underwriting.AppraisalCompanyName`|`string`|`extract`|Appraisal company name|Padove Appraisal Service|
|`Underwriting.TotalBorrowerIncome`|`number`|`extract`|Total borrower income|12956.70|
|`Underwriting.QualifyingRateType`|`array`|`generate`|Qualifying rate type selection(s)||
|`Underwriting.QualifyingRateType.*`|`string`|`extract`|||
|`Underwriting.QualifyingRatePercentage`|`number`|`extract`|Rate used for qualifying|6.5000|
|`Underwriting.InitialBoughtDownRatePercentage`|`number`|`extract`|Initial bought-down rate|6.5000|
|`Underwriting.OtherQualifyingRatePercentage`|`number`|`extract`|Other qualifying rate|6.5000|
|`Underwriting.ProposedMonthlyPaymentTotal`|`number`|`extract`|Total proposed monthly payment for the property|4148.96|
|`Underwriting.FundsRequiredToClose`|`number`|`extract`|Borrower funds to close|400000|
|`Underwriting.VerifiedAssetsAmount`|`number`|`extract`|Verified borrower assets amount|1000000|
|`Seller`|`object`|`generate`|Extracted seller information||
|`Seller.Name`|`string`|`extract`|Seller name|CMG Home Loans|
|`Seller.Address`|`string`|`extract`|Seller address|470 S Cedar Crest Blvd, Allentown, PA 18103|
|`Seller.Number`|`string`|`extract`|Seller number|S12345|
|`Seller.LoanNumber`|`string`|`extract`|Seller loan number|78jwyfovn264ldyhzv200aleh677fb|
|`Seller.ContactName`|`string`|`extract`|Contact name|Andres Dicki|
|`Seller.ContactPhoneNumber`|`string`|`extract`|Contact phone number|(717) 238-8313|
|`Seller.InvestorLoanNumber`|`string`|`extract`|Investor loan number|987654|
