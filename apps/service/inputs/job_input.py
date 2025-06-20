import graphene

class JobneedModifiedAfterInput(graphene.InputObjectType):
    """Input to fetch job need details based on people id, business unit and client id."""
    peopleid=graphene.Int(required=True,description="People id")
    buid=graphene.Int(required=True,description="Business unit id")
    clientid=graphene.Int(required=True,description="Client id")


class JobneedDetailsModifiedAfterInput(graphene.InputObjectType):
    """Input to fetch job need details based on job need ids and client timezone offset."""
    jobneedids=graphene.String(required=True,description="Job need ids") # comma separated jobneedids
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")

class ExternalTourModifiedAfterInput(graphene.InputObjectType):
    """Input to fetch external tour details based on people id, business unit and client id."""
    peopleid=graphene.Int(required=True,description="People id")
    buid=graphene.Int(required=True,description="Business unit id")
    clientid=graphene.Int(required=True,description="Client id")

