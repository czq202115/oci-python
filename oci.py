import base64
import oci

# 配置文件路径，根据实际情况修改
config_file = "D:\\桌面\\乌龟壳\\boit\\config.txt"
config = oci.config.from_file(config_file)

compute_client = oci.core.ComputeClient(config)
virtual_network_client = oci.core.VirtualNetworkClient(config)

compartment_id = config["tenancy"]  # 替换为适当的 Compartment OCID

# 获取可用的实例形状（shape）
shapes = compute_client.list_shapes(compartment_id=compartment_id).data

# 打印可用的形状列表
print("Available shapes:")
for i, shape in enumerate(shapes, start=1):
    print(f"{i}. {shape.shape}")

# 让用户选择形状
selected_shape_index = int(input("Select the shape: ")) - 1
if selected_shape_index < 0 or selected_shape_index >= len(shapes):
    print("Invalid shape selected.")
    exit(1)

selected_shape = shapes[selected_shape_index]
shape_name = selected_shape.shape

cpu_count = int(input("Enter the number of CPUs: "))
memory_size = int(input("Enter the memory size (in GB): "))

# 获取适用于所选形状的 Ubuntu 镜像
images = compute_client.list_images(compartment_id=compartment_id, shape=shape_name).data
ubuntu_images = [image for image in images if image.operating_system == "Canonical Ubuntu" and image.launch_mode == "NATIVE"]
if not ubuntu_images:
    print("No available Ubuntu images found for the selected shape.")
    exit(1)

# 选择第一个镜像
selected_image = ubuntu_images[0]
image_id = selected_image.id


# 创建 IdentityClient
identity_client = oci.identity.IdentityClient(config)

# 获取可用性域列表
availability_domains = identity_client.list_availability_domains(compartment_id=compartment_id).data

# 打印可用的可用性域列表
print("Available availability domains:")
for i, domain in enumerate(availability_domains, start=1):
    print(f"{i}. {domain.name}")

# 让用户选择可用性域
selected_domain_index = int(input("Select the availability domain: ")) - 1
if selected_domain_index < 0 or selected_domain_index >= len(availability_domains):
    print("Invalid availability domain selected.")
    exit(1)

selected_domain = availability_domains[selected_domain_index]
availability_domain = selected_domain.name

boot_volume_size = int(input("Enter the boot volume size (in GB): "))
vpu_per_gb = int(input("Enter the VPU per GB value: "))

ssh_key = "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA7FBvcR4RoSlPjD0Kcm2vN+VhMPvLY70cpIdCYDvf8p1o0J0ZKZEMFBDmtsEdDezrptS/fxEMlUuwcN65/+A8Zquep649Yvi6CgVch51igF2YOpOqyReqijuKoRV9p1Wui6rS21UeepYT1C4hseclm0a0HItuaiwoRzcEDIG4ywlYXBPSEBCZSDTHI57pS+xi30xXWNCnLPunctirlrneZwM55Vykxa3iDcuF8Rg+uYyUkQ2PhouixCGIVmLu3mJKoxB4Gp3bkZdsQs8WNaWBD+ZBZY6Hnr67vesYwpqk2BaeY5GgUAI1LKa1u2tr1DeGfyd8nfxQJCTii9GIamccdw=="  # 替换为您的 SSH 公钥内容
root_password = input("Enter the root password: ")

# 获取可用的 VCN 列表
vcns = virtual_network_client.list_vcns(compartment_id=compartment_id).data

if vcns:
    # 选择第一个 VCN
    selected_vcn = vcns[0]
    vcn_id = selected_vcn.id
    print("Using existing VCN:", selected_vcn.display_name)
else:
    # 创建新的 VCN
    create_vcn_response = virtual_network_client.create_vcn(
        oci.core.models.CreateVcnDetails(
            compartment_id=compartment_id,
            cidr_block="10.0.0.0/16",  # 替换为适当的 CIDR 块
            display_name="MyVCN"
        )
    )

    vcn = create_vcn_response.data
    vcn_id = vcn.id
    print("New VCN created with ID:", vcn_id)
    # 获取可用子网列表
subnets = virtual_network_client.list_subnets(compartment_id=compartment_id).data

if subnets:
    # 选择第一个子网
    selected_subnet = subnets[0]
    subnet_id = selected_subnet.id
    print("Using existing subnet:", selected_subnet.display_name)
else:
    # 创建新的子网
    create_subnet_response = virtual_network_client.create_subnet(
        oci.core.models.CreateSubnetDetails(
            compartment_id=compartment_id,
            availability_domain=availability_domain,
            vcn_id=vcn_id,
            cidr_block="10.0.0.0/24",  # 替换为适当的 CIDR 块
            display_name="MySubnet"
        )
    )

    subnet = create_subnet_response.data
    subnet_id = subnet.id
    print("New subnet created with ID:", subnet_id)
# 创建引导卷配置
create_boot_volume_request = oci.core.models.CreateBootVolumeDetails(
    availability_domain=availability_domain,
    compartment_id=compartment_id,
    size_in_gbs=boot_volume_size,
    display_name="MyBootVolume",
    vpus_per_gb=vpu_per_gb
)

# 创建实例的请求参数
create_instance_request = oci.core.models.LaunchInstanceDetails(
    compartment_id=compartment_id,
    availability_domain=availability_domain,
    shape=shape_name,
    display_name="MyInstance",
    image_id=image_id,
    subnet_id=subnet_id,
    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
        ocpus=cpu_count,
        memory_in_gbs=memory_size
    ),
    attach_boot_volume_details=oci.core.models.AttachBootVolumeDetails(
        boot_volume_id=None,  # 此处留空，由系统自动生成
        create_details=create_boot_volume_request
    ),
    metadata={
        "ssh_authorized_keys": ssh_key,
        "user_data": base64.b64encode(('''#!/bin/bash
echo root:{} |sudo chpasswd root
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config;
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config;
sudo service sshd restart
'''.format(root_password)).encode()).decode()
    }
)

# 发起创建实例请求
create_instance_response = compute_client.launch_instance(create_instance_request)

# 等待实例状态变为 "RUNNING"
instance_id = create_instance_response.data.id
oci.wait_until(
    compute_client,
    compute_client.get_instance(instance_id),
    "lifecycle_state",
    "RUNNING"
)

# 获取实例的公共 IP 地址
instance = compute_client.get_instance(instance_id).data
#public_ip = instance.metadata["public_ip"]

# 打印实例的公共 IP 地址和其他信息
print("Instance created successfully.")
print("Info :", instance)
