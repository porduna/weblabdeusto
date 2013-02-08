import os
import sha
import time
import random
import datetime
import threading

from wtforms.fields.core import UnboundField
from wtforms.validators import Email

from sqlalchemy.sql.expression import desc

from flask import Markup, request, redirect, abort, url_for, flash, Response

from flask.ext.wtf import Form, TextField, Required, PasswordField, SelectField, NumberRange

from flask.ext.admin.contrib.sqlamodel import ModelView
from flask.ext.admin import expose, AdminIndexView, BaseView
from flask.ext.admin.model.form import InlineFormAdmin

import weblab.configuration_doc as configuration_doc
import weblab.db.model as model
import weblab.permissions as permissions

from weblab.admin.web.filters import get_filter_number, generate_filter_any
from weblab.admin.web.fields import DisabledTextField

def get_app_instance():
    import weblab.admin.web.app as admin_app
    return admin_app.AdministrationApplication.INSTANCE

class AdministratorView(BaseView):

    def is_accessible(self):
        return get_app_instance().is_admin()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(request.url.split('/weblab/administration')[0] + '/weblab/client')

        return super(AdministratorView, self)._handle_view(name, **kwargs)

class MyProfileView(AdministratorView):

    @expose()
    def index(self):
        return redirect(request.url.split('/weblab/administration')[0] + '/weblab/administration/profile')

class AdministratorModelView(ModelView):

    def is_accessible(self):
        return get_app_instance().is_admin()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(request.url.split('/weblab/administration')[0] + '/weblab/client')

        return super(AdministratorModelView, self)._handle_view(name, **kwargs)


    # 
    # TODO XXX FIXME: This may be a bug. However, whenever this is commented,
    # Flask-Admin does this:
    #
    #       # Auto join
    #       for j in self._auto_joins:
    #                   query = query.options(subqueryload(j))
    # 
    # And some (weird) results in UserUsedExperiment are not shown, while other yes
    # 
    def scaffold_auto_joins(self):
        return []

SAME_DATA = object()

def get_full_url(url):
    script_name   = get_app_instance().script_name
    return script_name + url
    

def show_link(klass, filter_name, field, name, view = 'View'):
    instance      = klass.INSTANCE
    url           = get_full_url(instance.url)

    link = u'<a href="%s?' % url

    if isinstance(filter_name, basestring):
        filter_numbers = [ getattr(instance, u'%s_filter_number' % filter_name) ]
    else:
        filter_numbers = [ getattr(instance, u'%s_filter_number' % fname) for fname in filter_name]

    if isinstance(name, basestring):
        names = [name]
    else:
        names = name

    for pos, (filter_number, name) in enumerate(zip(filter_numbers, names)):
        if '.' not in name:
            data = getattr(field, name)
        else:
            variables = name.split('.')
            current = field
            data = None
            for variable in variables:
                current = getattr(current, variable)
                if current is None:
                    data = ''
                    break
            if data is None:
                data = current
        link += u'flt%s_%s=%s&' % (pos + 1, filter_number, data)

    if view == SAME_DATA:
        view = data

    link = link[:-1] + u'">%s</a>' % view

    return Markup(link)
   
class UserAuthForm(InlineFormAdmin):
    def postprocess_form(self, form_class):
        form_class.configuration = PasswordField('configuration', description = 'Detail the password (DB), Facebook ID -the number- (Facebook), OpenID identifier.')
        return form_class

class UsersPanel(AdministratorModelView):

    column_list = ('role', 'login', 'full_name', 'email', 'groups', 'logs', 'permissions')
    column_searchable_list = ('full_name', 'login')
    column_filters = ( 'full_name', 'login','role', 'email'
                    ) + generate_filter_any(model.DbGroup.name.property.columns[0], 'Group', model.DbUser.groups)


    form_excluded_columns = 'avatar',
    form_args = dict(email = dict(validators = [Email()]) )

    column_descriptions = dict( login     = 'Username (all letters, dots and numbers)', 
                                full_name ='First and Last name',
                                email     = 'Valid e-mail address',
                                avatar    = 'Not implemented yet, it should be a public URL for a user picture.' )

    inline_models = (UserAuthForm(model.DbUserAuth),)

    column_formatters = dict(
                            role        = lambda c, u, p: show_link(UsersPanel,              'role', u, 'role.name', SAME_DATA),
                            groups      = lambda c, u, p: show_link(GroupsPanel,             'user', u, 'login'),
                            logs        = lambda c, u, p: show_link(UserUsedExperimentPanel, 'user', u, 'login'),
                            permissions = lambda c, u, p: show_link(UserPermissionPanel,     'user', u, 'login'),
                        )

    INSTANCE = None

    def __init__(self, session, **kwargs):
        super(UsersPanel, self).__init__(model.DbUser, session, **kwargs)
        self.login_filter_number = get_filter_number(self, u'User.login')
        self.group_filter_number = get_filter_number(self, u'Group.name')
        self.role_filter_number  = get_filter_number(self, u'Role.name')

        self.local_data = threading.local()

        UsersPanel.INSTANCE = self

    def edit_form(self, obj = None):
        form = super(UsersPanel, self).edit_form(obj)
        self.local_data.authentications = {}
        if obj is not None:
            for auth_instance in obj.auths:
                self.local_data.authentications[auth_instance.id] = (auth_instance.auth.name, auth_instance.configuration)
        return form

    def on_model_change(self, form, user_model):
        auths = set()
        for auth_instance in user_model.auths:
            if auth_instance.auth in auths:
                raise Exception("You can not have two equal auth types (of type %s)" % auth_instance.auth.name)
            else:
                auths.add(auth_instance.auth)
               
                if hasattr(self.local_data, 'authentications'):

                    old_auth_type, old_auth_conf = self.local_data.authentications.get(auth_instance.id, (None, None))
                    if old_auth_type == auth_instance.auth.name and old_auth_conf == auth_instance.configuration:
                        # Same as before: ignore
                        continue

                    if not auth_instance.configuration:
                        # User didn't do anything here. Restoring configuration.
                        auth_instance.configuration = old_auth_conf or ''
                        continue

                self._on_auth_changed(auth_instance)
                    

    def _on_auth_changed(self, auth_instance):
        if auth_instance.auth.auth_type.name.lower() == 'db':
            password = auth_instance.configuration
            if len(password) < 6:
                raise Exception("Password too short")
            auth_instance.configuration = self._password2sha(password)
        elif auth_instance.auth.auth_type.name.lower() == 'facebook':
            try:
                int(auth_instance.configuration)
            except:
                raise Exception("Use a numeric ID for Facebook")
        # Other validations would be here


    def _password2sha(self, password):
        # TODO: Avoid replicating
        randomstuff = ""
        for _ in range(4):
            c = chr(ord('a') + random.randint(0,25))
            randomstuff += c
        password = password if password is not None else ''
        return randomstuff + "{sha}" + sha.new(randomstuff + password).hexdigest()

class GroupsPanel(AdministratorModelView):

    column_searchable_list = ('name',)
    column_list = ('name','parent', 'users','permissions')

    column_filters = ( ('name',) 
                        + generate_filter_any(model.DbUser.login.property.columns[0], 'User login', model.DbGroup.users)
                        + generate_filter_any(model.DbUser.full_name.property.columns[0], 'User name', model.DbGroup.users)
                    )

    column_formatters = dict(
                            users       = lambda c, g, p: show_link(UsersPanel,           'group', g, 'name'),
                            permissions = lambda c, g, p: show_link(GroupPermissionPanel, 'group', g, 'name'),
                        )

    INSTANCE = None

    def __init__(self, session, **kwargs):
        super(GroupsPanel, self).__init__(model.DbGroup, session, **kwargs)

        self.user_filter_number  = get_filter_number(self, u'User.login')

        GroupsPanel.INSTANCE = self

class UserUsedExperimentPanel(AdministratorModelView):

    column_auto_select_related = True
    column_select_related_list = ('user',)
    can_delete = False
    can_edit   = False
    can_create = False

    column_searchable_list = ('origin',)
    column_sortable_list = ('UserUsedExperiment.id', ('user', model.DbUser.login), ('experiment',  model.DbExperiment.id), 'start_date', 'end_date', 'origin', 'coord_address')
    column_list    = ( 'user', 'experiment', 'start_date', 'end_date', 'origin', 'coord_address','details')
    column_filters = ( 'user', 'start_date', 'end_date', 'experiment', 'origin', 'coord_address')

    column_formatters = dict(
                    user       = lambda c, uue, p: show_link(UsersPanel, 'login', uue, 'user.login', SAME_DATA),
                    experiment = lambda c, uue, p: show_link(ExperimentPanel, ('name', 'category'), uue, ('experiment.name', 'experiment.category.name'), uue.experiment ),
                    details    = lambda c, uue, p: Markup('<a href="%s">Details</a>' % (url_for('.detail', id=uue.id))),
                )

    action_disallowed_list = ['create','edit','delete']

    INSTANCE = None

    def __init__(self, files_directory, session, **kwargs):
        super(UserUsedExperimentPanel, self).__init__(model.DbUserUsedExperiment, session, **kwargs)

        self.files_directory     = files_directory
        if type(self) == UserUsedExperimentPanel:
            self.user_filter_number  = get_filter_number(self, u'User.login')
        self.experiment_filter_number  = get_filter_number(self, u'Experiment.name')
        # self.experiment_category_filter_number  = get_filter_number(self, u'Category.name')

        if type(self) == UserUsedExperimentPanel:
            UserUsedExperimentPanel.INSTANCE = self

    def get_list(self, page, sort_column, sort_desc, search, filters, *args, **kwargs):
        # So as to sort descending, force sorting by 'id' and reverse the sort_desc

        if sort_column is None:
            sort_column = 'start_date'
            sort_desc   = not sort_desc

            # If that fails, try to avoid it using a different sort_column
            try:
                return super(UserUsedExperimentPanel, self).get_list(page, sort_column, sort_desc, search, filters, *args, **kwargs)
            except:
                sort_column = 'UserUsedExperiment_start_date'
                return super(UserUsedExperimentPanel, self).get_list(page, sort_column, sort_desc, search, filters, *args, **kwargs)
       
        return super(UserUsedExperimentPanel, self).get_list(page, sort_column, sort_desc, search, filters, *args, **kwargs)

    @expose('/details/<int:id>')
    def detail(self, id):
        uue = self.get_query().filter_by(id = id).first()
        if uue is None:
            return abort(404)

        properties = {}
        for prop in uue.properties:
            properties[prop.property_name.name] = prop.value

        return self.render("details.html", uue = uue, properties = properties)

    @expose('/interactions/<int:id>')
    def interactions(self, id):
        uue = self.get_query().filter_by(id = id).first()

        if uue is None:
            return abort(404)

        interactions = []

        for command in uue.commands:
            timestamp = time.mktime(command.timestamp_before.timetuple()) + 1e-6 * command.timestamp_before_micro
            interactions.append((timestamp, True, command))

        for f in uue.files:
            timestamp = time.mktime(f.timestamp_before.timetuple()) + 1e-6 * f.timestamp_before_micro
            interactions.append((timestamp, False, f))

        interactions.sort(lambda (x1, x2, x3), (y1, y2, y3) : cmp(x1, y1))

        return self.render("interactions.html", uue = uue, interactions = interactions, unicode = unicode)

    def get_file(self, id):
        return self.session.query(model.DbUserFile).filter_by(id = id).first()

    @expose('/files/<int:id>')
    def files(self, id):
        uf = self.get_file(id)
        if uf is None:
            return abort(404)

        if 'not stored' in uf.file_sent:
            flash("File not stored")
            return self.render("error.html", message = "The file has not been stored. Check the %s configuration value." % configuration_doc.CORE_STORE_STUDENTS_PROGRAMS)
        
        file_path = os.path.join(self.files_directory, uf.file_sent)
        if os.path.exists(file_path):
            content = open(file_path).read()
            return Response(content, headers = {'Content-Type' : 'application/octstream', 'Content-Disposition' : 'attachment; filename=file_%s.bin' % id})
        else:
            if os.path.exists(self.files_directory):
                flash("Wrong configuration or file deleted")
                return self.render("error.html", message = "The file was stored, but now it is not reachable. Check the %s property." % configuration_doc.CORE_STORE_STUDENTS_PROGRAMS_PATH)
            else:
                flash("Wrong configuration")
                return self.render("error.html", message = "The file was stored, but now it is not reachable. The %s directory does not exist." % configuration_doc.CORE_STORE_STUDENTS_PROGRAMS_PATH)


class ExperimentCategoryPanel(AdministratorModelView):
   
    column_searchable_list = ('name',)
    column_list    = ('name', 'experiments')
    column_filters = ( 'name', ) 

    column_formatters = dict(
                    experiments = lambda co, c, p: show_link(ExperimentPanel, 'category', c, 'name')
                )

    INSTANCE = None

    def __init__(self, session, **kwargs):
        super(ExperimentCategoryPanel, self).__init__(model.DbExperimentCategory, session, **kwargs)
        
        self.category_filter_number  = get_filter_number(self, u'Category.name')

        ExperimentCategoryPanel.INSTANCE = self

class ExperimentPanel(AdministratorModelView):
    
    column_searchable_list = ('name',)
    column_list = ('category', 'name', 'start_date', 'end_date', 'uses')

    
    column_filters = ('name','category')

    column_formatters = dict(
                        category = lambda c, e, p: show_link(ExperimentCategoryPanel, 'category', e, 'category.name', SAME_DATA),
                        uses     = lambda c, e, p: show_link(UserUsedExperimentPanel, 'experiment', e, 'name'),
                )

    INSTANCE = None

    def __init__(self, session, **kwargs):
        super(ExperimentPanel, self).__init__(model.DbExperiment, session, **kwargs)
        
        self.name_filter_number  = get_filter_number(self, u'Experiment.name')
        self.category_filter_number  = get_filter_number(self, u'Category.name')
        ExperimentPanel.INSTANCE = self

def display_parameters(context, permission, p):
    parameters = u''
    for parameter in permission.parameters:
        parameters += u'%s = %s, ' % (parameter.permission_type_parameter, parameter.value)
    permission_str = u'%s(%s)' % (permission.permission_type, parameters[:-2])
    return permission_str

class GenericPermissionPanel(AdministratorModelView):
    
    """ Abstract class for UserPermissionPanel, GroupPermissionPanel and RolePermissionPanel """

    can_create = False

    column_descriptions = dict(permanent_id = 'A unique permanent identifier for a particular permission',)
    column_searchable_list = ('permanent_id', 'comments')
    column_formatters = dict( permission = display_parameters )
    column_filters = ( 'permission_type', 'permanent_id', 'date', 'comments' )
    column_sortable_list = ( 'permission', 'permanent_id', 'date', 'comments')
    column_list = ('permission', 'permanent_id', 'date', 'comments')
    form_overrides       = dict( permanent_id = DisabledTextField, permission_type = DisabledTextField )

    def __init__(self, model, session, **kwargs):
        super(GenericPermissionPanel, self).__init__(model, session, **kwargs)


    def get_list(self, page, sort_column, sort_desc, search, filters, *args, **kwargs):
        # So as to sort descending, force sorting by 'id' and reverse the sort_desc
        if sort_column is None:
            sort_column = 'date'
            sort_desc   = not sort_desc
        return super(GenericPermissionPanel, self).get_list(page, sort_column, sort_desc, search, filters, *args, **kwargs)


    def on_model_change(self, form, permission):
        # TODO: use weblab.permissions directly
        req_arguments = {
            'experiment_allowed' : ('experiment_permanent_id','experiment_category_id','time_allowed'),
            'admin_panel_access' : ('full_privileges',),
            'access_forward'     : (),
        }
        opt_arguments = {
            'experiment_allowed' : ('priority','initialization_in_accounting'),
            'admin_panel_access' : (),
            'access_forward'     : (),
        }
        required_arguments = set(req_arguments[permission.permission_type])
        optional_arguments = set(opt_arguments[permission.permission_type])
        obtained_arguments = set([ parameter.permission_type_parameter for parameter in permission.parameters ])

        missing_arguments  = required_arguments.difference(obtained_arguments)
        exceeded_arguments = obtained_arguments.difference(required_arguments.union(optional_arguments))

        message = ""
        if missing_arguments:
            message = "Missing arguments: %s" % ', '.join(missing_arguments)
            if exceeded_arguments:
                message += "; "
        if exceeded_arguments:
            message += "Exceeded arguments: %s" % ', '.join(exceeded_arguments)
        if message:
            raise Exception(message)

        if permission.permission_type == 'experiment_allowed':
            exp_name     = [ parameter for parameter in permission.parameters if parameter.permission_type_parameter == 'experiment_permanent_id' ][0].value
            cat_name     = [ parameter for parameter in permission.parameters if parameter.permission_type_parameter == 'experiment_category_id'  ][0].value
            time_allowed = [ parameter for parameter in permission.parameters if parameter.permission_type_parameter == 'time_allowed'            ][0].value
            
            found = False
            for exp in self.session.query(model.DbExperiment).filter_by(name = exp_name).all():
                if exp.category.name == cat_name:
                    found = True
                    break
            if not found:
                raise Exception(u"Experiment not found: %s@%s" % (exp_name, cat_name))
            
            try:
                int(time_allowed)
            except:
                raise Exception("Time allowed must be a number (in seconds)")



class PermissionEditForm(InlineFormAdmin):

    def postprocess_form(self, form_class):
        form_class.permission_type_parameter = UnboundField(DisabledTextField)
        return form_class

class UserPermissionPanel(GenericPermissionPanel):

    column_filters       = GenericPermissionPanel.column_filters       + ('user',)
    column_sortable_list = GenericPermissionPanel.column_sortable_list + (('user',model.DbUser.login),)
    column_list          = ('user', )  + GenericPermissionPanel.column_list

    inline_models = (PermissionEditForm(model.DbUserPermissionParameter),)

    INSTANCE = None

    def __init__(self, session, **kwargs):
        super(UserPermissionPanel, self).__init__(model.DbUserPermission, session, **kwargs)
        self.user_filter_number = get_filter_number(self, u'User.login')
        UserPermissionPanel.INSTANCE = self

class GroupPermissionPanel(GenericPermissionPanel):

    column_filters       = GenericPermissionPanel.column_filters       + ('group',)
    column_sortable_list = GenericPermissionPanel.column_sortable_list + (('group',model.DbGroup.name),)
    column_list          = ('group', )  + GenericPermissionPanel.column_list

    inline_models = (PermissionEditForm(model.DbGroupPermissionParameter),)

    INSTANCE = None

    def __init__(self, session, **kwargs):
        super(GroupPermissionPanel, self).__init__(model.DbGroupPermission, session, **kwargs)

        self.group_filter_number = get_filter_number(self, u'Group.name')
        
        GroupPermissionPanel.INSTANCE = self

class RolePermissionPanel(GenericPermissionPanel):

    column_filters       = GenericPermissionPanel.column_filters       + ('role',)
    column_sortable_list = GenericPermissionPanel.column_sortable_list + (('role',model.DbRole.name),)
    column_list          = ('role', )  + GenericPermissionPanel.column_list

    inline_models = (PermissionEditForm(model.DbRolePermissionParameter),)

    INSTANCE = None

    def __init__(self, session, **kwargs):
        super(RolePermissionPanel, self).__init__(model.DbRolePermission, session, **kwargs)
        
        self.role_filter_number = get_filter_number(self, u'Role.name')

        RolePermissionPanel.INSTANCE = self

class PermissionsForm(Form):
    permission_types = SelectField(u"Permission type:", choices=[ (permission_type, permission_type) for permission_type in permissions.permission_types ], default = permissions.EXPERIMENT_ALLOWED)
    recipients       = SelectField(u"Type of recipient:", choices=[('user', 'User'), ('group', 'Group'), ('role', 'Role')], default = 'group')


class PermissionsAddingView(AdministratorView):

    PERMISSION_FORMS = {}

    def __init__(self, session, **kwargs):
        self.session = session
        super(PermissionsAddingView, self).__init__(**kwargs)

    @expose(methods=['POST','GET'])
    def index(self):
        form = PermissionsForm()
        if form.validate_on_submit():
            if form.recipients.data == 'user': 
                return redirect(url_for('.users', permission_type = form.permission_types.data))
            elif form.recipients.data == 'role': 
                return redirect(url_for('.roles', permission_type = form.permission_types.data))
            elif form.recipients.data == 'group': 
                return redirect(url_for('.groups', permission_type = form.permission_types.data))

        return self.render("admin-permissions.html", form=form)

    def _get_permission_form(self, permission_type, recipient_type, recipient_resolver, DbPermissionClass, DbPermissionParameterClass):
        key = u'%s__%s' % (permission_type, recipient_type)
        if key in self.PERMISSION_FORMS:
            return self.PERMISSION_FORMS[key]()
    
        # Otherwise, generate it
        current_permission_type = permissions.permission_types[permission_type]

        session = self.session

        class ParentPermissionForm(Form):

            comments   = TextField("Comments")
            recipients = SelectField(recipient_type, description="Recipients of the permission")

            def get_permanent_id(self):
                recipient = recipient_resolver(self.recipients.data)
                return u'%s::%s' % (permission_type, recipient)

            def add_permission(self):
                recipient = recipient_resolver(self.recipients.data)
                db_permission = DbPermissionClass( recipient, permission_type, permanent_id = self.get_permanent_id(), date = datetime.datetime.today(), comments = self.comments.data )
                session.add(db_permission)

                return db_permission

            def add_parameters(self, db_permission):
                for parameter in current_permission_type.parameters:
                    data = getattr(self, parameter.name).data
                    db_parameter = DbPermissionParameterClass( db_permission, parameter.name, data)
                    db_permission.parameters.append(db_parameter)
                    session.add(db_parameter)

            def self_register(self):
                db_permission = self.add_permission()
                self.add_parameters(db_permission)
                session.commit()

        ###################################################################################
        # 
        # If a permission requires a special treatment, this is where it should be placed
        # 
        if permission_type == permissions.EXPERIMENT_ALLOWED:
            
            class ParticularPermissionForm(ParentPermissionForm):
                parameter_list = ['experiment', 'time_allowed', 'priority', 'initialization_in_accounting']

                experiment = SelectField(u'Experiment', description = "Experiment")

                time_allowed = TextField(u'Time assigned',                  description = "Measured in seconds",  validators = [Required(), NumberRange(min=1)], default=100)
                priority     = TextField(u'Priority',                       description = "Priority of the user", validators = [Required(), NumberRange(min=0)], default=5)
                initialization_in_accounting = SelectField(u'Initialization', description = "Take initialization into account",  choices = [('1','Yes'),('0','No')], default='1')


                def __init__(self, *args, **kwargs):
                    super(ParticularPermissionForm, self).__init__(*args, **kwargs)
                    choices = []
                    for exp in session.query(model.DbExperiment).all():
                        exp_id = u'%s@%s' % (exp.name, exp.category.name)
                        choices.append((exp_id, exp_id))
                    self.experiment.choices = choices

                def get_permanent_id(self):
                    recipient = recipient_resolver(self.recipients.data)
                    exp_name, cat_name = self.experiment.data.split('@')
                    return u'%s::%s@%s::%s' % (permission_type, exp_name, cat_name, recipient)

                def add_parameters(self, db_permission):

                    db_parameter = DbPermissionParameterClass( db_permission, permissions.TIME_ALLOWED, self.time_allowed.data)
                    db_permission.parameters.append(db_parameter)
                    session.add(db_parameter)

                    db_parameter = DbPermissionParameterClass( db_permission, permissions.PRIORITY, self.priority.data)
                    db_permission.parameters.append(db_parameter)
                    session.add(db_parameter)

                    db_parameter = DbPermissionParameterClass( db_permission, permissions.INITIALIZATION_IN_ACCOUNTING, self.initialization_in_accounting.data)
                    db_permission.parameters.append(db_parameter)
                    session.add(db_parameter)

                    exp_name, cat_name = self.experiment.data.split('@')

                    db_parameter = DbPermissionParameterClass( db_permission, permissions.EXPERIMENT_PERMANENT_ID, exp_name)
                    db_permission.parameters.append(db_parameter)
                    session.add(db_parameter)

                    db_parameter = DbPermissionParameterClass( db_permission, permissions.EXPERIMENT_CATEGORY_ID, cat_name)
                    db_permission.parameters.append(db_parameter)
                    session.add(db_parameter)


        ###################################################################################
        # 
        #  Otherwise, it is automatically generated
        # 
        else: # Auto-generate it by default
            parameters_code =  """    parameter_list = %s\n""" % repr([ parameter.name for parameter in current_permission_type.parameters ])
            for parameter in current_permission_type.parameters:
                parameters_code += """    %s = TextField(u"%s", description="%s", validators = [Required()])\n""" % (
                                            parameter.name,
                                            parameter.name.replace('_',' ').capitalize(),
                                            parameter.description )

            form_code = """class ParticularPermissionForm(ParentPermissionForm):\n""" + parameters_code
            
            context = {}
            context.update(globals())
            context.update(locals())

            exec form_code in context, context

            ParticularPermissionForm = context['ParticularPermissionForm']

        self.PERMISSION_FORMS[key] = ParticularPermissionForm
        return ParticularPermissionForm()

    def _check_permission_type(self, permission_type):
        current_permission_type = permissions.permission_types.get(permission_type, None)
        if current_permission_type is None:
            raise abort(400) # TODO:  show an error
       
    def _show_form(self, permission_type, recipient_type, recipients, recipient_resolver, DbPermissionClass, DbPermissionParameterClass, back_url):
        current_permission_type = permissions.permission_types[permission_type]
        form = self._get_permission_form(permission_type, recipient_type, recipient_resolver, DbPermissionClass, DbPermissionParameterClass)
        form.recipients.choices = recipients

        if form.validate_on_submit():
            try:
                form.self_register()
            except:
                flash("Error saving data. May the permission be duplicated?")
                return self.render("admin-permission-create.html", form = form, fields = form.parameter_list, description = current_permission_type.description, permission_type = permission_type)
            return redirect(back_url)


        return self.render("admin-permission-create.html", form = form, fields = form.parameter_list, description = current_permission_type.description, permission_type = permission_type)

    @expose('/users/<permission_type>/', methods = ['GET', 'POST'])
    def users(self, permission_type):
        self._check_permission_type(permission_type)

        users = [ (user.login, u'%s - %s' % (user.login, user.full_name)) for user in self.session.query(model.DbUser).order_by(desc('id')).all() ]

        recipient_resolver = lambda login: self.session.query(model.DbUser).filter_by(login = login).one()
    
        return self._show_form(permission_type, 'Users', users, recipient_resolver, 
                                model.DbUserPermission, model.DbUserPermissionParameter, 
                                get_full_url(UserPermissionPanel.INSTANCE.url))

    @expose('/groups/<permission_type>/', methods = ['GET','POST'])
    def groups(self, permission_type):
        self._check_permission_type(permission_type)

        groups = [ (g.name, g.name) for g in self.session.query(model.DbGroup).order_by(desc('id')).all() ]

        recipient_resolver = lambda group_name: self.session.query(model.DbGroup).filter_by(name = group_name).one()

        return self._show_form(permission_type, 'Groups', groups, recipient_resolver, 
                                model.DbGroupPermission, model.DbGroupPermissionParameter,
                                get_full_url(GroupPermissionPanel.INSTANCE.url))


    @expose('/roles/<permission_type>/', methods = ['GET','POST'])
    def roles(self, permission_type):
        self._check_permission_type(permission_type)

        roles = [ (r.name, r.name) for r in self.session.query(model.DbRole).order_by(desc('id')).all() ]
        
        recipient_resolver = lambda role_name: self.session.query(model.DbRole).filter_by(name = role_name).one()

        return self._show_form(permission_type, 'Roles', roles, recipient_resolver, 
                                model.DbRolePermission, model.DbRolePermissionParameter,
                                get_full_url(RolePermissionPanel.INSTANCE.url))


class HomeView(AdminIndexView):

    def __init__(self, db_session, **kwargs):
        self._db_session = db_session
        super(HomeView, self).__init__(**kwargs)

    @expose()
    def index(self):
        return self.render("admin-index.html")

    def is_accessible(self):
        return get_app_instance().INSTANCE.is_admin()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(request.url.split('/weblab/administration')[0] + '/weblab/client')

        return super(HomeView, self)._handle_view(name, **kwargs)


