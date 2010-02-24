#include "statetypes.h"
#include "stdio.h"

//SERVICE CALENDAR METHODS

ServiceCalendar*
scNew( ) {
    ServiceCalendar* ret = (ServiceCalendar*)malloc(sizeof(ServiceCalendar));
    ret->head = NULL;
    ret->num_sids = 0;
    ret->sid_str_to_int = create_hashtable_string(16);
    ret->sid_int_to_str = (char**)malloc(256*sizeof(char*));
    
    return ret;
}

int
scAddServiceId( ServiceCalendar* this, char* service_id ) {
    int* sid_int_payload = (int*)malloc(sizeof(int));
    *sid_int_payload = this->num_sids;
    hashtable_insert_string( this->sid_str_to_int, service_id, sid_int_payload );
    
    size_t labelsize = strlen(service_id)+1;
    char* sid_str_payload = (char*)malloc(labelsize*sizeof(char));
    strcpy(sid_str_payload, service_id);
    this->sid_int_to_str[this->num_sids]=sid_str_payload;
    
    int ret = this->num_sids;
    this->num_sids += 1;
    return ret;
}

char*
scGetServiceIdString( ServiceCalendar* this, int service_id ) {
    if( service_id < 0 || service_id >= this->num_sids) {
        return NULL;
    }
    return this->sid_int_to_str[service_id];
}

int
scGetServiceIdInt( ServiceCalendar* this, char* service_id ) {
    int *ret = (int*)hashtable_search( this->sid_str_to_int, service_id );
    if( ret==NULL ){
        return scAddServiceId(this, service_id );
    } else {
        return *ret;
    }
}

void
scAddPeriod( ServiceCalendar* this, ServicePeriod* period ) {
    if(!this->head) {
        this->head = period;
    } else {
        ServicePeriod* prev = NULL;
        ServicePeriod* curs = this->head;
        
        while(curs && period->begin_time >= curs->end_time ) {
            prev = curs;
            curs = curs->next_period;
        }
        
        //link last and period; replace the head if necessary
        if(prev) {
            prev->next_period = period;
        } else {
            this->head = period;
        }
        period->prev_period = prev;
        
        //link period and curs
        period->next_period = curs;
        //curs could be the end of the linked list, in which case next is NULL
        if(curs){
            curs->prev_period = period;
        }
        
    }
}

ServicePeriod*
scPeriodOfOrAfter( ServiceCalendar* this, long time ) {
  ServicePeriod* period = this->head;

  while( period && period->end_time <= time ) {
    period = period->next_period;
  }
  
  return period;
}

ServicePeriod*
scPeriodOfOrBefore( ServiceCalendar* this, long time ) {
  if(!this->head) {
    return NULL;
  }
    
  ServicePeriod* period = spFastForward( this->head );

  while( period && period->begin_time > time ) {
    period = period->prev_period;
  }
  return period;
}

ServicePeriod*
scHead( ServiceCalendar* this ) { return this->head; }

void
scDestroy( ServiceCalendar* this ) {
    ServicePeriod* curs = this->head;
    ServicePeriod* next;

    while(curs) {
      next = curs->next_period;
      spDestroyPeriod(curs);
      curs = next;
    }
    
    hashtable_destroy( this->sid_str_to_int, 1 ); //destroy sid directory, and sid strings themselves
    int i;
    for(i=0; i<this->num_sids; i++) {
        free(this->sid_int_to_str[i]);
    }
    free(this->sid_int_to_str);

    free(this);
}

//SERVICEPERIOD METHODS

ServicePeriod* spNew( long begin_time, long end_time, int n_service_ids, ServiceId* service_ids ) {
  ServicePeriod* ret = (ServicePeriod*)malloc(sizeof(ServicePeriod));
  ret->begin_time    = begin_time;
  ret->end_time      = end_time;
  ret->n_service_ids = n_service_ids;
  ret->service_ids  = (ServiceId*)malloc(n_service_ids*sizeof(ServiceId));
  memcpy( ret->service_ids, service_ids, n_service_ids*sizeof(ServiceId) );
  ret->prev_period = NULL;
  ret->next_period = NULL;

  return ret;
}

void
spDestroyPeriod( ServicePeriod* this ) {
  free( this->service_ids );
  free( this );
}


int
spPeriodHasServiceId( ServicePeriod* this, ServiceId service_id) {
  int i;
  for(i=0; i<this->n_service_ids; i++) {
    if( this->service_ids[i] == service_id ) {
      return 1;
    }
  }
  return 0;
}

ServicePeriod*
spRewind( ServicePeriod* this ) {
  while( this->prev_period ) {
    this = this->prev_period;
  }
  return this;
}

ServicePeriod*
spFastForward( ServicePeriod* this ) {
  while( this->next_period ) {
    this = this->next_period;
  }
  return this;
}

void
spPrint( ServicePeriod* this ) {
  ServicePeriod* curr = spRewind( this );
  while( curr->next_period ) {
    spPrintPeriod( curr );
    curr = curr->next_period;
  }
}

void
spPrintPeriod( ServicePeriod* this ) {
  printf( "time=%ld..%ld service_ids=[", this->begin_time, this->end_time );
  int i;
  for(i=0; i<this->n_service_ids; i++) {
    printf("%d", this->service_ids[i]);
    if( i != this->n_service_ids-1 )
      printf(", ");
  }
  printf( "]\n" );
}

long
spBeginTime( ServicePeriod* this ) {
	return this->begin_time;
}

long
spEndTime( ServicePeriod* this ) {
	return this->end_time;	
}

ServiceId*
spServiceIds( ServicePeriod* this, int* count ) {
	*count = this->n_service_ids;
	return this->service_ids;
}

ServicePeriod*
spNextPeriod(ServicePeriod* this) {
	return this->next_period;
}

ServicePeriod*
spPreviousPeriod(ServicePeriod* this) {
	return this->prev_period;
}

void
spPrint( ServicePeriod* this );

inline long
spDatumMidnight( ServicePeriod* this, int timezone_offset ) {
    /*Returns the unix time corresponding to the local time of the last midnight to occur 
      before the beginning of this service peroid. Typically, triphops specify events relative
      to this datum*/
    
    long since_local_midnight = (this->begin_time+timezone_offset)%SECS_IN_DAY;
    return this->begin_time - since_local_midnight;
}

inline long
spNormalizeTime( ServicePeriod* this, int timezone_offset, long time ) {
    /* Normalizes unix time to seconds since the last midnight before the beginning of the service period */
    
    long midnight = spDatumMidnight( this, timezone_offset );
    
    return time-midnight;
}

Timezone*
tzNew( ) {
    Timezone* ret = (Timezone*)malloc(sizeof(Timezone));
    ret->head = NULL;
    
    return ret;
}

void
tzAddPeriod( Timezone* this, TimezonePeriod* period ) {
    if(!this->head) {
        this->head = period;
    } else {
        TimezonePeriod* prev = NULL;
        TimezonePeriod* curs = this->head;
        
        while(curs && period->begin_time > curs->end_time ) {
            prev = curs;
            curs = curs->next_period;
        }
        
        //link last and period; replace the head if necessary
        if(prev) {
            prev->next_period = period;
        } else {
            this->head = period;
        }
        
        //link period and curs
        period->next_period = curs;
        
    }
}

TimezonePeriod* cached_period = NULL;
long cached_begin_time = 0;
long cached_end_time = 0;

TimezonePeriod*
tzPeriodOf( Timezone* this, long time) {
  
  TimezonePeriod* period = NULL;
  
  if (cached_period != NULL && time >= cached_begin_time && time <= cached_end_time) {
  	period = cached_period;
  	//printf("using cached period\n");
  }
  else {
    //printf("searching for period\n");
    period = this->head;

    while( period && period->end_time < time ) {
      period = period->next_period;
    }
    
    if( period && time < period->begin_time ) {
      return NULL;
    }
    
    cached_period = period;
    cached_begin_time = period->begin_time;
    cached_end_time = period->end_time;
  }
  
  return period;
}

int
tzUtcOffset( Timezone* this, long time) {
    //Returns seconds offset UTC for this timezone, at the given time
    
    TimezonePeriod* now = tzPeriodOf( this, time );
    
    if( !now ) {
        return -100*3600; //utc offset larger than any conceivable offset, as an error signal
    }
    
    return tzpUtcOffset( now );
}

int
tzTimeSinceMidnight( Timezone* this, long time ) {
    TimezonePeriod* now = tzPeriodOf( this, time );
    
    if( !now ) {
        return -1;
    }
    
    return (time+now->utc_offset)%SECS_IN_DAY;
}

TimezonePeriod*
tzHead( Timezone* this ) {
    return this->head;
}

void
tzDestroy( Timezone* this ) {
    TimezonePeriod* curs = this->head;
    TimezonePeriod* next;

    while(curs) {
      next = curs->next_period;
      tzpDestroy(curs);
      curs = next;
    }

    free(this);
}

TimezonePeriod*
tzpNew( long begin_time, long end_time, int utc_offset ) {
    TimezonePeriod* ret = (TimezonePeriod*)malloc(sizeof(TimezonePeriod));
    ret->begin_time    = begin_time;
    ret->end_time      = end_time;
    ret->utc_offset    = utc_offset;
    ret->next_period = NULL;

    return ret;
}

void
tzpDestroy( TimezonePeriod* this ) {
    free( this );
}

int
tzpUtcOffset( TimezonePeriod* this ) {
    return this->utc_offset;
}

int
tzpTimeSinceMidnight( TimezonePeriod* this, long time ) {
    return (time+this->utc_offset)%SECS_IN_DAY;
}

long
tzpBeginTime( TimezonePeriod* this ) {
    return this->begin_time;
}

long
tzpEndTime( TimezonePeriod* this ) {
    return this->end_time;
}

TimezonePeriod*
tzpNextPeriod(TimezonePeriod* this) {
    return this->next_period;
}
