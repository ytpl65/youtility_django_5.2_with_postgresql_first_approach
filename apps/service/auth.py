from apps.core.exceptions import (
    NoClientPeopleError,MultiDevicesError, NotRegisteredError,
    WrongCredsError, NoSiteError, NotBelongsToClientError)
from apps.peoples.models import People
from logging import getLogger
log = getLogger('mobile_service_log')

class Messages:
    AUTHFAILED     = "Authentication Failed "
    AUTHSUCCESS    = "Authentication Successfull"
    NOSITE         = "Unable to find site!"
    INACTIVE       = "Inactive client or people"
    NOCLIENTPEOPLE = "Unable to find client or People or User/Client are not verified"
    MULTIDEVICES   = "Cannot login on multiple devices, Please logout from the other device"
    WRONGCREDS     = "Incorrect Username or Password"
    NOTREGISTERED  = "Device Not Registered"
    NOTBELONGSTOCLIENT = "UserNotInThisClient"

def LoginUser(response, request):
    if response['isauthenticated']:
        People.objects.filter(
            id = response['user'].id).update(
                deviceid = response['authinput'].deviceid)

def LogOutUser(response, request):
    if response['isauthenticated']:
        People.objects.filter(
            id = response['user'].id).update(
                deviceid = -1
            )

def check_user_site(user):
    return user.bu_id not in [1, None, 'NONE', 'None']


def auth_check(info, input, returnUser, uclientip = None):
    from django.contrib.auth import authenticate
    from graphql.error import GraphQLError
    try:
        log.info(f"Authenticating {input.loginid} for {input.clientcode}")
        if valid_user := People.objects.select_related('client').filter(loginid = input.loginid, client__bucode = input.clientcode).exists():
            user = authenticate(
                info.context,
                username = input.loginid,
                password = input.password)
            if not user: raise ValueError
        else: raise NotBelongsToClientError(Messages.NOTBELONGSTOCLIENT)
    except ValueError as e:
        raise WrongCredsError(Messages.WRONGCREDS) from e
    else:
        if not check_user_site(user): raise NoSiteError(Messages.NOSITE)
        allowAccess = isValidDevice = isUniqueDevice = True
        people_validips = user.client.bupreferences['validip']
        people_validimeis = user.client.bupreferences["validimei"].replace(" ", "").split(",")

        if people_validips is not None and len(people_validips.replace(" ", "")) > 0:
            clientIpList = people_validips.replace(" ", "").split(",")
            if uclientip is not None and uclientip not in clientIpList:
                allowAccess = False
        
        if user.deviceid in [-1, '-1'] or input.deviceid in [-1, '-1']:
            allowAccess=True
        elif user.deviceid != input.deviceid: raise MultiDevicesError(Messages.MULTIDEVICES)
        allowAccess = True
        if allowAccess:
            if user.client.enable and user.enable:
                return returnUser(user, info.context), user
            else:
                raise NoClientPeopleError(Messages.NOCLIENTPEOPLE)

def authenticate_user(input, request, msg, returnUser):
    loginid = input.loginid
    password = input.password
    deviceid = input.deviceid

    from graphql import GraphQLError
    from django.contrib.auth import authenticate

    user = authenticate(request, username = loginid, password = password)
    if not user: raise WrongCredsError(msg.WRONGCREDS)
    valid_imeis = user.client.bupreferences["validimei"].replace(" ", "").split(",")

    if deviceid != '-1' and user.deviceid == '-1':
        if all([user.client.enable, user.enable, user.isverified]):
            return returnUser(user, request), user
        raise NoClientPeopleError(msg.NOCLIENTPEOPLE)
    if deviceid not in valid_imeis:
        raise NotRegisteredError(msg.NOTREGISTERED)
    if deviceid != user.deviceid:
        raise MultiDevicesError(msg.MULTIDEVICES)
    return returnUser(user, request), user
