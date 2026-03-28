import django.db.models.fields.files
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0002_add_product_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='productrating',
            name='review_photo',
            field=models.ImageField(blank=True, null=True, upload_to='review_photos/'),
        ),
    ]
