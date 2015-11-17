import datetime

from django.shortcuts import render
from django.views.generic import View
from django.template import RequestContext, loader, Engine
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from deals.models import Deal, STATE_CHOICES, EPOCH_CHOICES


class DealListBaseView(View):
    """ Base class for other Deal listing views.
        It implements a default get method allowing subclassing views to 
        render fully functional deal listings by simply overriding the 
        default class level options.

        Subclassing views can still override and implement their own get or post
        methods. However these methods can call the base 'render_deal_list' method
        which returns the rendered deal list as a string.
    """

    # default deal list options as class level vars:

    deals = Deal.objects.all()  # can be any queryset of Deal instances
    title = "Deals"
    description = ""
    zero_items_message = "Sorry, no deals found!"
    num_page_items = 15
    min_orphan_items = 2
    show_page_num = 1
    pagination_base_url = ""
    date_filter = { 'choices': EPOCH_CHOICES, 'default': -1 }

        
    def render_deal_list(self, request, **kwargs):
        """ Takes a queryset of of deal
        """

        # update the default options with any specified as kwargs:
        for arg_name in kwargs:
            try:
                setattr(self, arg_name, kwargs.get(arg_name))
            except:
                pass

        # use date filter parameter to filter deals if specified:
        self.filter_deals_from_params(request)

        # paginate deals and get the specified page:
        paginator = Paginator(
            self.deals, 
            self.num_page_items,
            self.min_orphan_items,
        )
        try:
            # get the page number if present in request.GET
            show_page_num = request.GET.get('pg')
            if not show_page_num:
                show_page_num = self.show_page_num
            deals_page = paginator.page(show_page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver first page.
            deals_page = paginator.page(1)
        except EmptyPage:
            # if page is out of range, deliver last page of results.
            deals_page = paginator.page(paginator.num_pages)

        # set the description to be used in the list header:
        if deals_page.paginator.count:
            description = self.description
        else:
            description = self.zero_items_message

        # combine them all into listing dictionary:
        deals_listing =  {
            'deals_page': deals_page,
            'date_filter': self.date_filter,
            'title': self.title,
            'description': description,
            'pagination_base_url': self.pagination_base_url,
        }

        # set the context and render the template to a string:
        deals_list_context = RequestContext( request, { 'listing': deals_listing } )
        template = loader.get_template('snippet_deal_listing.html')
        rendered_template = template.render(deals_list_context)
                    
        #  return the rendered template string:
        return rendered_template


    def filter_deals_from_params(self, request):
        """ uses any date filter parameter specified in the query string to filter deals.
        """

        date_filter_param = request.GET.get('dtf')
        if not date_filter_param:
            return

        try:
            date_filter_param = int(date_filter_param)
        except:
            return

        choices = self.date_filter.get('choices', [])
        if date_filter_param < 0 or date_filter_param >= len(choices):
            return

        date_filter_delta = choices[date_filter_param][0]
        if date_filter_delta != -1:
            filter_date = datetime.date.today() - datetime.timedelta(days=date_filter_delta)
            self.deals = self.deals.filter(date_last_modified__gt=filter_date)
        
        self.date_filter['default'] = date_filter_delta


    def get(self, request, *args, **kwargs):
        """ returns a full featured deals-listing page showing
            the deals set in 'deals' class variable.
        """
        context = {
            'rendered_deal_list': self.render_deal_list(request),
            'search_options': {
                'query': "",
                'states': { 'choices': STATE_CHOICES, 'default': 25 },
            }
        }
        return render(request, 'deals/deal_list_base.html', context)


class CollectionsBaseView(View):
    """ Handles rendering of items in a collection
    """
    zero_items_message = "Sorry, no collection items found!"
    num_page_items = 9
    min_orphan_items = 3
    show_page_num = 1
    pagination_base_url = ""
    queryset = ""
    title = "Collection listing"
    description = "See all collection items"
    template = ''

    def get(self, *args, **kwargs):

        engine = Engine.get_default()
        template = engine.get_template(self.template)

        # paginate deals and get the specified page:
        paginator = Paginator(
            self.queryset,
            self.num_page_items,
            self.min_orphan_items,
        )

        try:
            # get the page number if present in request.GET
            show_page_num = self.request.GET.get('pg')
            if not show_page_num:
                show_page_num = self.show_page_num
            collections_page = paginator.page(show_page_num)
        except PageNotAnInteger:
            # if page is not an integer, deliver first page.
            collections_page = paginator.page(1)
        except EmptyPage:
            # if page is out of range, deliver last page of results.
            collections_page = paginator.page(paginator.num_pages)

        # set the description to be used in the list header:
        if collections_page.paginator.count:
            description = self.description
        else:
            description = self.zero_items_message

        context = RequestContext(
                self.request,
                {'search_options': {
                    'query': "",
                    'states': {'choices': STATE_CHOICES, 'default': 25},
                },
                'collections_page': collections_page,
                'title': self.title,
                'description': description,
                'pagination_base_url': self.pagination_base_url,
                'page': True,
            })

        return render(self.request, self.template, context)


class DealCollectionItemsListBaseView(DealListBaseView):
    """ Renders a list of collection items
    """
    title = ''
    queryset = ''
    slug_name = ''
    model = ''
    not_found = ''
    template = ''
    filter_field = ''

    def get_queryset(self, slug):
        """Returns query set
        """
        self.queryset = self.model.objects.get(slug=slug)
        return self.queryset
    
    def get(self, *args, **kwargs):
        """Attends to GET request
        """
        slug = self.kwargs.get(self.slug_name)
        try:
            self.get_queryset(slug)
        except self.model.DoesNotExist:
            raise Http404(self.not_found)
        self.filter_deals(**kwargs)
        self.set_title("some title")
        self.set_description("some desc")
        self.do_render()
        
    def set_context_data(self):
        """Sets context for response
        """
        self.context = {
            'search_options': {
                'query': "",
                'states': {'choices': STATE_CHOICES, 'default': 25},
            },
            'rendered_deal_list': self.rendered_deal_list
        }

    def set_description(self, desc):
        """Sets description on list page
        """
        self.description = desc 
    
    def set_title(self, title):
        """Sets title on list page
        """
        self.title = title
    
    def filter_deals(self, **filter):
        """Applies filter to deal query set
        """
        self.deals = Deal.objects.filter(**filter)
    
    def do_render(self):
        """Renders template
        """
        self.rendered_deal_list = self.render_deal_list(
                self.request,
                deals=self.deals,
                title=self.title,
                description=self.description
            )
        self.set_context_data()
        return render(self.request, self.template, self.context)
