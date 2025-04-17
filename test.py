# import maxminddb

# print(maxminddb.__version__)

# ipv4_reader = maxminddb.open_database('data/geo-whois-asn-country-ipv4.mmdb')
# ipv6_reader = maxminddb.open_database('data/geo-whois-asn-country-ipv6.mmdb')

# # Open the MMDB file
# ipv4_address = '146.52.107.86'
# ipv6_address = '2a02:810a:14a7:5f00:a7e9:25fe:eeac:2e02'

# print(ipv4_reader.get(ipv4_address), ipv4_address)
# print(ipv6_reader.get(ipv6_address), ipv6_address)

# from mastodon import Mastodon

# Mastodon.create_app(
#     'web',
#     api_base_url = 'https://fediway.com',
#     to_file = 'pytooter_clientcred.secret'
# )

# import matplotlib.pyplot as plt
# from lifelines import KaplanMeierFitter
# import numpy as np

# durations = np.array([1739, 3468, 2705, 1439])
# durations = (durations / 364.25)

# event_observed = [
#     0, 1, 0, 1
# ]

# kmf = KaplanMeierFitter()
# kmf.fit(durations, event_observed=event_observed)
# kmf.plot_survival_function()

# plt.title('Survival after OSCC Diagnosis')
# plt.xlabel('Years')
# plt.ylabel('Survival Probability')
# plt.savefig('surv_p2=1.png', dpi=300)

from confluent_kafka.admin import AdminClient

conf = {
    'bootstrap.servers': 'localhost:29092'  # Use this if running outside Docker
    # 'bootstrap.servers': 'kafka:9092'     # Use this if running inside Docker
}

admin_client = AdminClient(conf)
topics = admin_client.list_topics().topics

print("Available topics:", list(topics.keys()))


