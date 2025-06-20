import graphene

class QuestionModifiedFilterInput(graphene.InputObjectType):
    """Input to fetch question details based on modification timestamp and client id."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    clientid=graphene.Int(required=True,description="Client id")


class QuestionSetModifiedFilterInput(graphene.InputObjectType):
    """Input to fetch question set details based on modification timestamp, client id, bu id and people id."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    buid=graphene.Int(required=True,description="Bu id")
    clientid=graphene.Int(required=True,description="Client id")
    peopleid=graphene.Int(required=True,description="People id")

class QuestionSetBelongingModifiedFilterInput(graphene.InputObjectType):
    """Input to fetch question set belonging details based on modification timestamp, client id and bu id."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    buid=graphene.Int(required=True,description="Bu id")
    clientid = graphene.Int(required = True,description="Client Id")
    peopleid=graphene.Int(required=True,description="People id")