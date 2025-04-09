# import maxminddb

# print(maxminddb.__version__)

# ipv4_reader = maxminddb.open_database('data/geo-whois-asn-country-ipv4.mmdb')
# ipv6_reader = maxminddb.open_database('data/geo-whois-asn-country-ipv6.mmdb')

# # Open the MMDB file
# ipv4_address = '146.52.107.86'
# ipv6_address = '2a02:810a:14a7:5f00:a7e9:25fe:eeac:2e02'

# print(ipv4_reader.get(ipv4_address), ipv4_address)
# print(ipv6_reader.get(ipv6_address), ipv6_address)

from mastodon import Mastodon

Mastodon.create_app(
    'web',
    api_base_url = 'https://fediway.com',
    to_file = 'pytooter_clientcred.secret'
)