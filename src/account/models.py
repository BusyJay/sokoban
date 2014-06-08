from django.db import models
from django.contrib.auth import models as admin_models
import uuid
from django.utils import timezone


class SimpleUserManager(admin_models.BaseUserManager):
    def create_user(self, email, username, password=None):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=SimpleUserManager.normalize_email(email),
            username=username,
            uuid=str(uuid.uuid4()),
        )

        user.set_password(password)
        # we don't need them to activate account
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        user = self.create_user(email, username=username, password=password)
        user.is_staff = True
        user.is_active = True
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class SimpleUser(admin_models.AbstractBaseUser, admin_models.PermissionsMixin):
    uuid = models.CharField(max_length=36, unique=True, db_index=True,
                            default=lambda: str(uuid.uuid4()))
    username = models.CharField(max_length=40, unique=True, db_index=True)
    email = models.EmailField(max_length=254, unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    join_time = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    objects = SimpleUserManager()

    def __unicode__(self):
        return self.username

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return self.username
