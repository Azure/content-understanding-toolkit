| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Subject`|`object`|`generate`|Extracted subject information.||
|`Subject.PropertyAddress`|`string`|`extract`|Address of the property being appraised|8405 S Croddy Way, San Marcos, CA 92069|
|`Subject.BorrowerName`|`string`|`extract`|Name of the borrower|Alisha M. Pike|
|`Subject.PublicRecordOwner`|`string`|`extract`|Name of the legal owner of the property as recorded in public records|Alisha M. Pike|
|`Subject.LegalDescription`|`string`|`extract`|Formal description of the property|Lot 5, Block 10 of Sunnyside Acres|
|`Subject.AssessorParcelNumber`|`string`|`extract`|Unique number assigned to the property by the local tax assessor's office|99-35-93-17-77|
|`Subject.TaxYear`|`string`|`extract`|Year for which property taxes are being assessed|2010|
|`Subject.RealEstateTaxes`|`number`|`extract`|Amount of property taxes levied on the property for the specified tax year|6856|
|`Subject.OccupantType`|`array`|`generate`|Occupant of the property based on its use (e.g., Owner, Tenant, Vacant)||
|`Subject.OccupantType.*`|`string`|`extract`|||
|`Subject.IsPUD`|`boolean`|`extract`|Indicates whether the property is part of a planned unit development (PUD)|true|
|`Subject.HOAAmount`|`number`|`extract`|HOA amount (payment required), if applicable|642|
|`Subject.HOAPaymentInterval`|`array`|`generate`|Frequency of the HOA payment (e.g., per year, per month)||
|`Subject.HOAPaymentInterval.*`|`string`|`extract`|||
|`Subject.PropertyRightsAppraisedType`|`array`|`generate`|Type of property rights being appraised (e.g., Fee Simple, Leasehold, Other)||
|`Subject.PropertyRightsAppraisedType.*`|`string`|`extract`|||
|`Subject.OtherPropertyRightsAppraised`|`string`|`extract`|Description of other property rights being appraised, if applicable|Life Estate|
|`Subject.AssignmentType`|`array`|`generate`|Type of appraisal assignment (e.g., Purchase Transaction, Refinance Transaction, Other)||
|`Subject.AssignmentType.*`|`string`|`extract`|||
|`Subject.OtherAssignment`|`string`|`extract`|Description of other types of appraisal assignments, if provided|Market Value|
|`Subject.LenderOrClientName`|`string`|`extract`|Name of the lender or client|Jay Michael Law|
|`Subject.LenderOrClientAddress`|`string`|`extract`|Address of the lender or client|298 Buffalo RD W Bennett, STE 1, San Marcos, CA 92069|
|`Contract`|`object`|`generate`|Extracted contract information.||
|`Contract.Price`|`number`|`extract`|Agreed-upon price of the property as stated in the purchase contract|498605|
|`Contract.Date`|`date`|`extract`|Date on which the purchase contract was signed|2023-06-17|
|`Contract.PropertySellerOwnerOfPublicRecord`|`array`|`generate`|Indicates whether the seller is the owner of public record||
|`Contract.PropertySellerOwnerOfPublicRecord.*`|`string`|`extract`|||
|`Neighborhood`|`object`|`generate`|Extracted neighborhood information.||
|`Neighborhood.LocationType`|`array`|`generate`|Neighborhood location (e.g., Urban, Suburban, Rural)||
|`Neighborhood.LocationType.*`|`string`|`extract`|||
|`Neighborhood.BuiltUpType`|`array`|`generate`|Level of development within the neighborhood (e.g., Over 75%, 25-75%, Under 25%)||
|`Neighborhood.BuiltUpType.*`|`string`|`extract`|||
|`Neighborhood.GrowthType`|`array`|`generate`|Neighborhood growth trend (e.g., Rapid, Stable, Slow)||
|`Neighborhood.GrowthType.*`|`string`|`extract`|||
|`Neighborhood.PropertyValuesTrend`|`array`|`generate`|Trend in property values (e.g., Increasing, Stable, Declining)||
|`Neighborhood.PropertyValuesTrend.*`|`string`|`extract`|||
|`Neighborhood.DemandAndSupplyTrend`|`array`|`generate`|Balance of demand and supply (e.g., Shortage, In Balance, Over Supply)||
|`Neighborhood.DemandAndSupplyTrend.*`|`string`|`extract`|||
|`Neighborhood.MarketingTimeTrend`|`array`|`generate`|Time to market properties (e.g., Under 3 mths, 3-6 mths, Over 6 mths)||
|`Neighborhood.MarketingTimeTrend.*`|`string`|`extract`|||
|`Site`|`object`|`generate`|Extracted site information.||
|`Site.Utilities`|`object`|`generate`|Extracted site utilities information.||
|`Site.Utilities.ElectricityType`|`array`|`generate`|Electricity service (e.g., Public, Other)||
|`Site.Utilities.ElectricityType.*`|`string`|`extract`|||
|`Site.Utilities.OtherElectricity`|`string`|`extract`|Description of other electricity service|Solar Panels|
|`Site.Utilities.GasType`|`array`|`generate`|Gas service (e.g., Public, Other)||
|`Site.Utilities.GasType.*`|`string`|`extract`|||
|`Site.Utilities.OtherGas`|`string`|`extract`|Description of other gas service|Natural gas wells|
|`Site.Utilities.WaterType`|`array`|`generate`|Water service (e.g., Public, Other)||
|`Site.Utilities.WaterType.*`|`string`|`extract`|||
|`Site.Utilities.OtherWater`|`string`|`extract`|Description of other water service|Water rights|
|`Site.Utilities.SanitarySewerType`|`array`|`generate`|Sanitary sewer service (e.g., Public, Other)||
|`Site.Utilities.SanitarySewerType.*`|`string`|`extract`|||
|`Site.Utilities.OtherSanitarySewer`|`string`|`extract`|Description of other sanitary sewer service|Septic|
|`Site.FEMASpecialFloodArea`|`array`|`generate`|Located in a FEMA-designated Special Flood Hazard Area||
|`Site.FEMASpecialFloodArea.*`|`string`|`extract`|||
|`Site.FEMAFloodZone`|`string`|`extract`|FEMA flood zone|SFHA|
|`Site.FEMAMapNumber`|`string`|`extract`|FEMA map number|06037C1636G|
|`Site.FEMAMapDate`|`date`|`extract`|FEMA map date|2016-05-06|
|`Improvements`|`object`|`generate`|Extracted improvements information.||
|`Improvements.UnitsType`|`array`|`generate`|Units present on the property (e.g., One, One with Accessory Unit)||
|`Improvements.UnitsType.*`|`string`|`extract`|||
|`Improvements.Type`|`array`|`generate`|Unit type within the building (e.g., Det., Att., S-Det./End Unit)||
|`Improvements.Type.*`|`string`|`extract`|||
|`Improvements.Status`|`array`|`generate`|Construction status (e.g., Existing, Proposed, Under Const.)||
|`Improvements.Status.*`|`string`|`extract`|||
|`Improvements.DesignStyle`|`string`|`extract`|Architectural design style|BI-LEVEL|
|`Improvements.YearBuilt`|`integer`|`extract`|Year the property was originally constructed|1991|
|`Improvements.EffectiveAgeInYears`|`number`|`extract`|Effective age of the improvements|5|
|`Improvements.FoundationType`|`array`|`generate`|Foundation type(s) (e.g., Concrete Slab, Crawl Space, Full Basement, Partial Basement)||
|`Improvements.FoundationType.*`|`string`|`extract`|||
|`Improvements.BasementArea`|`number`|`extract`|Total basement area (sq. ft.)|1293|
|`Improvements.BasementFinish`|`number`|`extract`|Percentage of the basement area that is finished|87|
|`Improvements.DamageEvidenceType`|`array`|`generate`|Evidence of damage or issues (e.g., Infestation, Dampness, Settlement)||
|`Improvements.DamageEvidenceType.*`|`string`|`extract`|||
|`Improvements.DeficiencyPresence`|`array`|`generate`|Presence of physical deficiencies or adverse conditions affecting the property (Yes/No)||
|`Improvements.DeficiencyPresence.*`|`string`|`extract`|||
|`Improvements.Deficiencies`|`string`|`extract`|Description of physical deficiencies or adverse conditions|Plumbing issues causing water damage or sanitation problems.|
|`SalesComparisonApproach`|`object`|`generate`|Extracted sales comparison approach information.||
|`SalesComparisonApproach.ComparableSalePrice1`|`number`|`extract`|Sale price of comparable property #1|445021|
|`SalesComparisonApproach.ComparableSalePrice2`|`number`|`extract`|Sale price of comparable property #2|370304|
|`SalesComparisonApproach.ComparableSalePrice3`|`number`|`extract`|Sale price of comparable property #3|355356|
|`SalesComparisonApproach.IndicatedValue`|`number`|`extract`|Indicated value of the subject property by sales comparison|501938|
|`Reconciliation`|`object`|`generate`|Extracted reconciliation information.||
|`Reconciliation.IndicatedValueBySalesComparisonApproach`|`number`|`extract`|Indicated value by sales comparison approach|501938|
|`Reconciliation.IndicatedValueByCostApproach`|`number`|`extract`|Indicated value by cost approach|500827|
|`Reconciliation.IndicatedValueByIncomeApproach`|`number`|`extract`|Indicated value by income approach|499716|
|`Reconciliation.AppraisalType`|`array`|`generate`|Type of appraisal (e.g., as is, subject to completion, subject to repairs, subject to required inspection)||
|`Reconciliation.AppraisalType.*`|`string`|`extract`|||
|`Reconciliation.AppraisedMarketValue`|`number`|`extract`|Final appraised market value of the subject property|501938|
|`Reconciliation.AppraisalEffectiveDate`|`date`|`extract`|Effective date of appraisal|2023-06-12|
|`PUDInfo`|`object`|`generate`|Extracted planned unit development information.||
|`PUDInfo.BuilderInControlOfHOA`|`array`|`generate`|Indicates whether the developer/builder is in control of the HOA (Yes/No)||
|`PUDInfo.BuilderInControlOfHOA.*`|`string`|`extract`|||
|`PUDInfo.UnitType`|`array`|`generate`|Unit type(s) within the PUD (e.g., Detached, Attached)||
|`PUDInfo.UnitType.*`|`string`|`extract`|||
|`PUDInfo.MultiDwellingUnitsPresence`|`array`|`generate`|Indicates whether the project contains any multi-dwelling units (Yes/No)||
|`PUDInfo.MultiDwellingUnitsPresence.*`|`string`|`extract`|||
|`Appraiser`|`object`|`generate`|Extracted appraiser information.||
|`Appraiser.Name`|`string`|`extract`|Name of the licensed appraiser|Ida Alice Stevens|
|`Appraiser.CompanyName`|`string`|`extract`|Name of the appraisal company|The Blackstone Group|
|`Appraiser.CompanyAddress`|`string`|`extract`|Physical address of the appraisal company|1313 Memorial Ave, Nashville, KS 08514|
|`Appraiser.PhoneNumber`|`string`|`extract`|Telephone number|801-022-5196|
|`Appraiser.Email`|`string`|`extract`|Email address|UYT@live.co|
|`Appraiser.SignatureAndReportDate`|`date`|`extract`|Date of signature and report|2023-06-17|
|`Appraiser.EffectiveDate`|`date`|`extract`|Effective date of appraisal|2023-06-17|
|`Appraiser.PropertyAppraisedAddress`|`string`|`extract`|Address of the property appraised|8405 S Croddy Way, San Marcos, CA 92069|
|`Appraiser.AppraisedValueOfSubjectProperty`|`number`|`extract`|Final appraised value of the subject property|501938|
|`Appraiser.SubjectPropertyStatus`|`array`|`generate`|Inspection status of the subject property||
|`Appraiser.SubjectPropertyStatus.*`|`string`|`extract`|||
|`Appraiser.ComparableSalesStatus`|`array`|`generate`|Inspection status of the comparable sales||
|`Appraiser.ComparableSalesStatus.*`|`string`|`extract`|||
|`Appraiser.Signature`|`string`|`classify`|Appraiser's signature presence classification|signed|
