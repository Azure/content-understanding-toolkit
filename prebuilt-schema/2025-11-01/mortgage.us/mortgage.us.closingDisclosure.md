| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Closing`|`object`|`generate`|Extracted closing information||
|`Closing.IssueDate`|`date`|`extract`|Issue date|2022-04-12|
|`Closing.Date`|`date`|`extract`|Closing date|2022-04-17|
|`Closing.DisbursementDate`|`date`|`extract`|Disbursement date|2022-04-21|
|`Closing.SettlementAgent`|`string`|`extract`|Settlement agent|Bright Title Co.|
|`Closing.FileNumber`|`string`|`extract`|File number|64-5681|
|`Closing.PropertyAddress`|`string`|`extract`|Property address|1634 W Glenoaks Blvd, Glendale, CA 91201|
|`Closing.SalePrice`|`number`|`extract`|Sale price|1800000|
|`Transaction`|`object`|`generate`|Extracted transaction information||
|`Transaction.BorrowerName`|`string`|`extract`|Borrower's name|Gwen Stacy|
|`Transaction.BorrowerAddress`|`string`|`extract`|Borrower's address|1634 W Glenoaks Blvd, Glendale, CA 91201|
|`Transaction.SellerName`|`string`|`extract`|Seller's name|Bonita Anderson|
|`Transaction.SellerAddress`|`string`|`extract`|Seller's address|920 University Blvd, Rexburg, CA 94954|
|`Transaction.LenderName`|`string`|`extract`|Lender's name|Skye AU Bank|
|`Transaction.BorrowerClosingCosts`|`number`|`extract`|Borrower's closing costs|17299.60|
|`Transaction.BorrowerCashToCloseType`|`array`|`generate`|Borrower's cash to close direction (From/To)||
|`Transaction.BorrowerCashToCloseType.*`|`string`|`extract`|||
|`Transaction.BorrowerCashToCloseAmount`|`number`|`extract`|Borrower's cash to close amount|70969.85|
|`Transaction.SellerCashToCloseType`|`array`|`generate`|Seller's cash to close direction (From/To)||
|`Transaction.SellerCashToCloseType.*`|`string`|`extract`|||
|`Transaction.SellerCashToCloseAmount`|`number`|`extract`|Seller's cash to close amount|275968.75|
|`Transaction.CoBorrowerNames`|`string`|`extract`|Full names of all co-borrowers as written on the form|Carmen Leannon|
|`Loan`|`object`|`generate`|Extracted loan information||
|`Loan.Term`|`string`|`extract`|Loan term|30 years|
|`Loan.Purpose`|`string`|`extract`|Loan purpose|Purchase|
|`Loan.Product`|`string`|`extract`|Loan product|Fixed Rate|
|`Loan.Type`|`array`|`generate`|Loan type selection(s)||
|`Loan.Type.*`|`string`|`extract`|||
|`Loan.OtherType`|`string`|`extract`|Other loan type (if provided)|RHS|
|`Loan.IdentificationNumber`|`string`|`extract`|Loan identification number|672047875|
|`Loan.MortgageInsuranceCaseNumber`|`string`|`extract`|Mortgage insurance case number|147188500|
|`Loan.Amount`|`number`|`extract`|Loan amount|1440000|
|`Loan.InterestRatePercentage`|`number`|`extract`|Interest rate percentage (0–100)|7.033|
|`Loan.MonthlyPrincipalAndInterest`|`number`|`extract`|Monthly principal and interest|9609.39|
|`Loan.EstimatedTaxInsuranceAndAssessmentsPerMonth`|`number`|`extract`|Estimated taxes, insurance and assessments per month|2525|
|`ApplicantSignature`|`string`|`classify`|Applicant's confirm receipt signature presence classification|signed|
|`CoApplicantSignature`|`string`|`classify`|Co-applicant's confirm receipt signature presence classification|unsigned|
