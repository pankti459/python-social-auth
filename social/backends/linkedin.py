"""
LinkedIn OAuth1 and OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/linkedin.html
"""
from social.backends.oauth import BaseOAuth1, BaseOAuth2


class BaseLinkedinAuth(object):
    EXTRA_DATA = [('id', 'id'),
                  ('first-name', 'first_name', True),
                  ('last-name', 'last_name', True),
                  ('firstName', 'first_name', True),
                  ('lastName', 'last_name', True)]
    USER_DETAILS = 'https://api.linkedin.com/v1/people/~:({0})'

    def get_user_details(self, response):
        """Return user details from Linkedin account"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response['firstName'],
            last_name=response['lastName']
        )
        email = response.get('emailAddress', '')
        return {'username': first_name + last_name,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_details_url(self):
        # use set() since LinkedIn fails when values are duplicated
        fields_selectors = list(set(['first-name', 'id', 'last-name'] +
                                self.setting('FIELD_SELECTORS', [])))
        # user sort to ease the tests URL mocking
        fields_selectors.sort()
        fields_selectors = ','.join(fields_selectors)
        return self.USER_DETAILS.format(fields_selectors)

    def user_data_headers(self):
        lang = self.setting('FORCE_PROFILE_LANGUAGE')
        if lang:
            return {
                'Accept-Language': lang if lang is not True
                                        else self.strategy.get_language()
            }

'''
class LinkedinOAuth(BaseLinkedinAuth, BaseOAuth1):
    """Linkedin OAuth authentication backend"""
    name = 'linkedin'
    SCOPE_SEPARATOR = '+'
    AUTHORIZATION_URL = 'https://www.linkedin.com/uas/oauth/authenticate'
    REQUEST_TOKEN_URL = 'https://api.linkedin.com/uas/oauth/requestToken'
    ACCESS_TOKEN_URL = 'https://api.linkedin.com/uas/oauth/accessToken'

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json(
            self.user_details_url(),
            params={'format': 'json'},
            auth=self.oauth_auth(access_token),
            headers=self.user_data_headers()
        )

    def unauthorized_token(self):
        """Makes first request to oauth. Returns an unauthorized Token."""
        scope = self.get_scope() or ''
        if scope:
            scope = '?scope=' + self.SCOPE_SEPARATOR.join(scope)
        return self.request(self.REQUEST_TOKEN_URL + scope,
                            params=self.request_token_extra_arguments(),
                            auth=self.oauth_auth()).text
'''

class LinkedinOAuth2(BaseLinkedinAuth, BaseOAuth2):
    name = 'linkedin-oauth2'
    SCOPE_SEPARATOR = ' '
    AUTHORIZATION_URL = 'https://www.linkedin.com/uas/oauth2/authorization'
    ACCESS_TOKEN_URL = 'https://www.linkedin.com/uas/oauth2/accessToken'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json(
            self.user_details_url(),
            params={'oauth2_access_token': access_token,
                    'format': 'json'},
            headers=self.user_data_headers()
        )

    def request_access_token(self, *args, **kwargs):
        # LinkedIn expects a POST request with querystring parameters, despite
        # the spec http://tools.ietf.org/html/rfc6749#section-4.1.3
        kwargs['params'] = kwargs.pop('data')
        return super(LinkedinOAuth2, self).request_access_token(
            *args, **kwargs
        )
    
class LinkedinOAuth(BaseOAuth2):
    name = 'linkedin'
    AUTHORIZATION_URL = \
        'https://www.linkedin.com/oauth/v2/authorization'
    ACCESS_TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'
    USER_DETAILS_URL = \
        'https://api.linkedin.com/v2/me?projection=({projection})'
    USER_EMAILS_URL = 'https://api.linkedin.com/v2/emailAddress' \
                      '?q=members&projection=(elements*(handle~))'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    DEFAULT_SCOPE = ['r_liteprofile']
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires_in', 'expires'),
        ('firstName', 'first_name'),
        ('lastName', 'last_name')
    ]

    def user_details_url(self):
        # use set() since LinkedIn fails when values are duplicated
        fields_selectors = list(set(['id', 'firstName', 'lastName'] +
                                    self.setting('FIELD_SELECTORS', [])))
        # user sort to ease the tests URL mocking
        fields_selectors.sort()
        fields_selectors = ','.join(fields_selectors)
        return self.USER_DETAILS_URL.format(projection=fields_selectors)

    def user_emails_url(self):
        return self.USER_EMAILS_URL

    def user_data(self, access_token, *args, **kwargs):
        response = self.get_json(
            self.user_details_url(),
            headers=self.user_data_headers(access_token)
        )

        if 'emailAddress' in set(self.setting('FIELD_SELECTORS', [])):
            emails = self.email_data(access_token, *args, **kwargs)
            if emails:
                response['emailAddress'] = emails[0]

        return response

    def email_data(self, access_token, *args, **kwargs):
        response = self.get_json(
            self.user_emails_url(),
            headers=self.user_data_headers(access_token)
        )
        email_addresses = []
        for element in response.get('elements', []):
            email_address = element.get('handle~', {}).get('emailAddress')
            email_addresses.append(email_address)
        return list(filter(None, email_addresses))

    def get_user_details(self, response):
        """Return user details from Linkedin account"""

        def get_localized_name(name):
            """
            FirstName & Last Name object
            {
                  "localized":{
                     "en_US":"Smith"
                  },
                  "preferredLocale":{
                     "country":"US",
                     "language":"en"
                  }
            }
            :return the localizedName from the lastName object
            """
            locale = "{}_{}".format(
                name["preferredLocale"]["language"],
                name["preferredLocale"]["country"]
            )
            return name['localized'].get(locale, '')

        fullname, first_name, last_name = self.get_user_names(
            first_name=get_localized_name(response['firstName']),
            last_name=get_localized_name(response['lastName'])
        )
        email = response.get('emailAddress', '')
        return {'username': first_name + last_name,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_data_headers(self, access_token):
        headers = {}
        lang = self.setting('FORCE_PROFILE_LANGUAGE')
        if lang:
            headers['Accept-Language'] = lang if lang is not True \
                else self.strategy.get_language()
        headers['Authorization'] = 'Bearer {access_token}'.format(
            access_token=access_token)
        return headers

    def request_access_token(self, *args, **kwargs):
        # LinkedIn expects a POST request with querystring parameters, despite
        # the spec http://tools.ietf.org/html/rfc6749#section-4.1.3
        kwargs['params'] = kwargs.pop('data')
        return super(LinkedinOAuth, self).request_access_token(
            *args, **kwargs
        )

    def process_error(self, data):
        super(LinkedinOAuth, self).process_error(data)
        if data.get('serviceErrorCode'):
            raise AuthCanceled(self, data.get('message') or data.get('status'))
