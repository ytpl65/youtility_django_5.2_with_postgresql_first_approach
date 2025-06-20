import graphene


class TypeAssistFilterInput(graphene.InputObjectType):
    """Input to fetch typeassist based on keys."""
    keys = graphene.List(graphene.String, required = True, description = "List of keys")

class TypeAssistModifiedFilterInput(graphene.InputObjectType):
    """Input to fetch typeassist based on modification timestamp and client id."""
    mdtz = graphene.String(required = True, description = "Modification timestamp")
    ctzoffset = graphene.Int(required = True, description = "Client timezone offset")
    clientid = graphene.Int(required = True, description = "Client id")