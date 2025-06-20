import graphene


class TicketFilterInput(graphene.InputObjectType):
    """Input to fetch ticket details based on people id, bu id, client id, modification timestamp and timezone offset."""
    peopleid=graphene.Int(required=True,description="People id")
    buid=graphene.Int(description="Bu id")
    clientid=graphene.Int(description="Client id")
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
