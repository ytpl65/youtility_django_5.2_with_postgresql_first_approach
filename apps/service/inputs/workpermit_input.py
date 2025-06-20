import graphene
from apps.service.types import GetPdfUrl


class WomPdfUrlFilterInput(graphene.InputObjectType):
    """Input to fetch pdf url based on wom uuid and people id."""
    wom_uuid = graphene.String(required=True,description="Wom uuid")
    peopleid = graphene.Int(required=True,description="People id")


class WomRecordFilterInput(graphene.InputObjectType):
    """Input to fetch wom records based on workpermit, people id, bu id, client id, fromdate and todate."""
    workpermit = graphene.String(required=True,description="Workpermit")
    peopleid = graphene.Int(required=True,description="People id")
    buid = graphene.Int(description="Bu id")
    parentid = graphene.Int(description="Parent id")
    clientid = graphene.Int(description="Client id")
    fromdate = graphene.String(required=True,description="From date")
    todate = graphene.String(required=True,description="To date")

class ApproveWorkpermitFilterInput(graphene.InputObjectType):
    """Input to approve workpermit based on people id, identifier and wom uuid."""
    peopleid = graphene.Int(required=True,description="People id")
    identifier = graphene.String(required=True,description="Identifier")
    wom_uuid = graphene.String(required=True,description="Wom uuid")

class RejectWorkpermitFilterInput(graphene.InputObjectType):
    """Input to reject workpermit based on people id, identifier and wom uuid."""
    peopleid = graphene.Int(required=True,description="People id")
    identifier = graphene.String(required=True,description="Identifier")
    wom_uuid = graphene.String(required=True,description="Wom uuid")

class ApproverFilterInput(graphene.InputObjectType):
    """Input to fetch approver based on bu id and client id."""
    buid = graphene.Int(required=True,description="Bu id")
    clientid = graphene.Int(required=True,description="Client id")


class VendorFilterInput(graphene.InputObjectType):
    """Input to fetch vendor based on bu id, client id, modification timestamp and timezone offset."""
    clientid = graphene.Int(required=True,description="Client id")
    mdtz = graphene.String(required=True,description="Modification timestamp")
    buid = graphene.Int(required=True,description="Bu id")
    ctzoffset = graphene.Int(required=True,description="Client timezone offset")
