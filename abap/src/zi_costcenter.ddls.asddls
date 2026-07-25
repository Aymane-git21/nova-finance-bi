// ===========================================================================
// NOT ACTIVATED - no ABAP system was available. See docs/adr/003-abap-evidence-strategy.md
// ===========================================================================
// ZI_CostCenter - master data interface view, three-level standard hierarchy.
//
// The hierarchy is exposed both ways on purpose: ParentId is the recursive
// edge, and the level attributes are denormalised onto the leaf. Both access
// patterns are needed - recursive walking for a hierarchy node, flat filtering
// for a query - and forcing every consumer to recurse just to filter by
// division is how a cost-centre report ends up slow.
// ===========================================================================

@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Cost centre - interface view'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #A,
  sizeCategory  : #S,
  dataClass     : #MASTER
}
@ObjectModel.representativeKey: 'CostCenter'
define view entity ZI_CostCenter
  as select from ztns_costcenter as CostCenter
{
      @ObjectModel.text.element: ['CostCenterName']
  key CostCenter.cost_center      as CostCenter,

      @Semantics.text: true
      CostCenter.cost_center_name as CostCenterName,

      CostCenter.company_code     as CompanyCode,

      // Hierarchy level 1.
      CostCenter.division_id      as DivisionId,
      @Semantics.text: true
      CostCenter.division_name    as DivisionName,

      // Hierarchy level 2.
      CostCenter.department_id    as DepartmentId,
      @Semantics.text: true
      CostCenter.department_name  as DepartmentName,

      // The recursive edge. Equals DepartmentId for a leaf.
      CostCenter.parent_id        as ParentId,
      CostCenter.hierarchy_level  as HierarchyLevel,

      // Support centre whose cost is allocated out at close. Drives the KA
      // allocation postings.
      CostCenter.is_overhead      as IsOverhead,

      @Semantics.businessDate.from: true
      CostCenter.valid_from       as ValidFrom,
      @Semantics.businessDate.to: true
      CostCenter.valid_to         as ValidTo

      // Deliberately NOT exposed: manager_user_id. Same reasoning as the
      // posting user on the journal - it is a pseudonymous token with no
      // business in an analytical consumption view.
}
