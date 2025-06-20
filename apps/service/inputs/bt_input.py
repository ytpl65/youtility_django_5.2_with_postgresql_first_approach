import graphene

class LocationFilterInput(graphene.InputObjectType):
    """Input to fetch location details based on modification timestamp and business unit."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    buid=graphene.Int(required=True,description="Business unit id")


class GeofenceFilterInput(graphene.InputObjectType):
    """Input to fetch geofence details based on site ids."""
    siteids=graphene.List(graphene.Int,required=True,description="List of site ids")

class ShiftFilterInput(graphene.InputObjectType):
    """Input to fetch shift details based on modification timestamp and business unit."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    buid=graphene.Int(required=True,description="Business unit id")
    clientid=graphene.Int(required=True,description="Client id")


class GroupsModifiedAfterFilterInput(graphene.InputObjectType):
    """Input to fetch group details based on modification timestamp and business unit."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    buid=graphene.Int(required=True,description="Business unit id")


class SiteListFilterInput(graphene.InputObjectType):
    """Input to fetch site list based on client id and people id."""
    clientid = graphene.Int(required=True,description="Client id")
    peopleid = graphene.Int(required=True,description="People id")

class SendEmailVerificationLinkFilterInput(graphene.InputObjectType):
    """Input to send email verification link based on client code and login id."""
    clientcode = graphene.String(required=True,description="Client code")
    loginid = graphene.String(required=True,description="Login id")


class SuperAdminMessageFilterInput(graphene.InputObjectType):
    """Input to fetch super admin message based on client id."""
    client_id = graphene.Int(required=True,description="Client id")

class SiteVisitedLogFilterInput(graphene.InputObjectType):
    """Input to fetch site visited log based on client id, people id and timezone offset."""
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    clientid=graphene.Int(required=True,description="Client id")
    peopleid=graphene.Int(required=True,description="People id")

class VerifyClientInput(graphene.InputObjectType):
    """Input to verify client code."""
    clientcode = graphene.String(required=True,description="Client code")