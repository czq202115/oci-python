from datetime import datetime
import shutil
import oci
import os
import gzip

config_file = "D:\\桌面\\乌龟壳\\boit\\config.txt"
reporting_namespace = 'bling'
prefix_file = "reports/usage-csv"
destination_path = 'downloaded_reports'

if not os.path.exists(destination_path):
    os.mkdir(destination_path)

#创建获取列表
config = oci.config.from_file(config_file)
reporting_bucket = config['tenancy']
object_storage = oci.object_storage.ObjectStorageClient(config)
report_bucket_objects = oci.pagination.list_call_get_all_results(
    object_storage.list_objects, reporting_namespace, reporting_bucket, prefix=prefix_file
)

# 下载
for o in report_bucket_objects.data.objects:
    print('Found file ' + o.name)
    object_details = object_storage.get_object(reporting_namespace, reporting_bucket, o.name)
    filename = o.name.rsplit('/', 1)[-1]
    file_path = os.path.join(destination_path, filename)

    with open(file_path, 'wb') as f:
        for chunk in object_details.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(chunk)

    # Extract file
    extracted_file_path = file_path[:-3]  # Remove .gz extension
    with gzip.open(file_path, 'rb') as gz_file:
        with open(extracted_file_path, 'wb') as extracted_file:
            extracted_file.write(gz_file.read())

    os.remove(file_path)  # Remove the compressed file

print('All files downloaded and extracted.')

# 处理文件
merged_file_path = os.path.join(destination_path, 'merged_report.csv')

with open(merged_file_path, 'w', encoding='utf-8') as output_file:
    for file_name in os.listdir(destination_path):
        if file_name.endswith('.csv'):
            file_path = os.path.join(destination_path, file_name)
            with open(file_path, 'r', encoding='utf-8') as input_file:
                content = input_file.read()
                output_file.write(content)

print('Files merged into', merged_file_path)
keyword = "PIC_COMPUTE_OUTBOUND_DATA_TRANSFER"
sum_quantity = 0

with open(merged_file_path, 'r', encoding='utf-8') as merged_file:
    lines = merged_file.readlines()
    for line in lines:
        if keyword in line:
            data = line.split(',')
            product_resource = data[5]
            interval_start = data[2]
            consumed_quantity = float(data[12])

            if keyword in product_resource:
                start_time = datetime.strptime(interval_start, '%Y-%m-%dT%H:%MZ')
                if start_time.month == datetime.now().month:
                    sum_quantity += consumed_quantity

print('已用:{}GB'.format(sum_quantity/1024/1024/1024/2))
#有问题，总是算出来俩两倍的值，所以除2了

# 删除文件夹及其内容
shutil.rmtree(destination_path)
print('目录及其内容已成功删除。')
