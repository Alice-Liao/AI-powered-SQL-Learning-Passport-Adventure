# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Admins(models.Model):
    user = models.OneToOneField('Users', models.DO_NOTHING, primary_key=True)

    class Meta:
        managed = False
        db_table = 'admins'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Countries(models.Model):
    cid = models.AutoField(primary_key=True)
    cname = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'countries'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class ErrorsRecord(models.Model):
    error_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    task = models.ForeignKey('Task', models.DO_NOTHING, blank=True, null=True)
    error_content = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'errors_record'


class Events(models.Model):
    eid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    month = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.ForeignKey(Countries, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'events'


class Food(models.Model):
    fid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    country = models.ForeignKey(Countries, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'food'


class LoginHistory(models.Model):
    login_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING)
    login_timestamp = models.DateTimeField()
    logout_timestamp = models.DateTimeField(blank=True, null=True)
    ip_address = models.CharField(max_length=45)
    login_status = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'login_history'


class MbRecord(models.Model):
    mb_id = models.AutoField(primary_key=True)
    content = models.CharField(blank=True, null=True)
    uid = models.ForeignKey('Users', models.DO_NOTHING, db_column='uid', blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mb_record'


class Messages(models.Model):
    message_id = models.AutoField(primary_key=True)
    sender = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    receiver = models.ForeignKey('Users', models.DO_NOTHING, related_name='messages_receiver_set', blank=True, null=True)
    message_content = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'messages'


class Places(models.Model):
    pid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.ForeignKey(Countries, models.DO_NOTHING, blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    visitors_per_year = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'places'


class Progress(models.Model):
    progress_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    progress_percentage = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'progress'


class QueryHistory(models.Model):
    query_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    task = models.ForeignKey('Task', models.DO_NOTHING, blank=True, null=True)
    query_content = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'query_history'


class Task(models.Model):
    tid = models.AutoField(primary_key=True)
    difficulty = models.IntegerField(blank=True, null=True)
    tname = models.CharField(max_length=100, blank=True, null=True)
    time = models.DateField(blank=True, null=True)
    hint = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=100, blank=True, null=True)
    cid = models.ForeignKey(Countries, models.DO_NOTHING, db_column='cid')
    expected_result = models.JSONField(blank=True, null=True)
    task_type = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'task'


class TaskStatus(models.Model):
    user = models.OneToOneField('Users', models.DO_NOTHING, primary_key=True)  # The composite primary key (user_id, task_id) found, that is not supported. The first column is selected.
    task = models.ForeignKey(Task, models.DO_NOTHING)
    status = models.IntegerField()
    date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'task_status'
        unique_together = (('user', 'task'),)


class Traveler(models.Model):
    user = models.OneToOneField('Users', models.DO_NOTHING, primary_key=True)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'traveler'


class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    email = models.CharField(unique=True, max_length=255)
    password = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'users'


class Visa(models.Model):
    vid = models.AutoField(primary_key=True)
    ispassed = models.BooleanField(blank=True, null=True)
    issuedate = models.DateField(blank=True, null=True)
    userid = models.ForeignKey(Users, models.DO_NOTHING, db_column='userid', blank=True, null=True)
    cid = models.ForeignKey(Countries, models.DO_NOTHING, db_column='cid')

    class Meta:
        managed = False
        db_table = 'visa'
