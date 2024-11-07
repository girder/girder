def is_nvidia_image(api, image):
    labels = api.inspect_image(image).get('Config', {}).get('Labels')
    return bool(labels and labels.get('com.nvidia.volumes.needed') == 'nvidia_driver')
