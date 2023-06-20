import oci

# 配置文件路径，根据实际情况修改
config_file = "D:\\桌面\\乌龟壳\\boit\\config.txt"
config = oci.config.from_file(config_file)

# 创建Client
client = oci.onesubscription.OrganizationSubscriptionClient(config)

# 获取当前用户的订阅列表
subscriptions = client.list_organization_subscriptions(config["tenancy"]).data
print(subscriptions)
# 打印订阅ID
# for subscription in subscriptions:
#     print("Subscription ID:", subscription.id)
