enum ev2citrusleaf_type { CL_NULL = 0x00, CL_INT = 0x01, CL_FLOAT = 2, CL_STR = 0x03, CL_BLOB = 0x04,
	CL_TIMESTAMP = 5, CL_DIGEST = 6, CL_JAVA_BLOB = 7, CL_CSHARP_BLOB = 8, CL_PYTHON_BLOB = 9, 
	CL_RUBY_BLOB = 10, CL_UNKNOWN = 666666};
typedef enum ev2citrusleaf_type ev2citrusleaf_type;

enum ev2citrusleaf_write_policy { CL_WRITE_ASYNC, CL_WRITE_ONESHOT, CL_WRITE_RETRY, CL_WRITE_ASSURED };

typedef enum ev2citrusleaf_write_policy ev2citrusleaf_write_policy;

typedef char ev2citrusleaf_bin_name[32];

//
// An object is the value in a bin, or it is used as a key
// The object is typed according to the citrusleaf typing system
// These are often stack allocated, and are assigned using the 'wrap' calls
//
//

//Config struct!
typedef struct config_s {
	const char* p_host;
	int port;
	const char* p_namespace;
	const char* p_set;
	int timeout_msec;
} config;
void event_enable_debug_mode(void);
//suppress logging
typedef enum {
	/**
	 * Pass this in cf_set_log_level() to suppress all logging.
	 */
	CF_NO_LOGGING = -1,

	/**
	 * Error condition has occurred.
	 */
	CF_ERROR,

	/**
	 * Unusual non-error condition has occurred.
	 */
	CF_WARN,

	/**
	 * Normal information message.
	 */
	CF_INFO,

	/**
	 * Message used for debugging purposes.
	 */
	CF_DEBUG
} cf_log_level;

void cf_set_log_level(cf_log_level level);

//LibEvent controls
struct event_base * event_base_new (void);
int event_base_dispatch (struct event_base *);
void event_base_free (struct event_base *);
int event_base_loopbreak(struct event_base *base);
int event_base_loopexit(struct event_base *base,
                        const struct timeval *tv);
// #define EVLOOP_ONCE             0x01
// #define EVLOOP_NONBLOCK         0x02
// #define EVLOOP_NO_EXIT_ON_EMPTY 0x04

int event_base_loop(struct event_base *base, int flags);
//ENDOF

//make this shit threadable
int evthread_use_pthreads(void);
int evthread_make_base_notifiable (struct event_base *base);
// Aerospike has made the cf_set_log_level function inaccessible.
// I have NO idea why.
// So expose their raw log_level var.
int32_t g_log_level;

// length is RIPEMD160_DIGEST_LENGTH from openssl
typedef struct { uint8_t digest[20]; } cf_digest;

typedef struct ev2citrusleaf_object_s {
	enum ev2citrusleaf_type    type;
	size_t			size;
	union {
		char 		*str; // note for str: size is strlen (not strlen+1 
		void 		*blob;
		int64_t		i64;   // easiest to have one large int type
	} u;

	void *free; // if this is set, this must be freed on destructuion	

} ev2citrusleaf_object;

// A bin is a name and an object

typedef struct ev2citrusleaf_bin_s {
	ev2citrusleaf_bin_name		bin_name;
	ev2citrusleaf_object			object;
} ev2citrusleaf_bin;

enum ev2citrusleaf_operation_type { CL_OP_WRITE, CL_OP_READ, CL_OP_ADD };

typedef struct ev2citrusleaf_operation_s {
	ev2citrusleaf_bin_name		bin_name;
	enum ev2citrusleaf_operation_type op;
	ev2citrusleaf_object		object;
} ev2citrusleaf_operation;

//
// All citrusleaf functions return an integer. This integer is 0 if the
// call has succeeded, and a negative number if it has failed.
// All returns of pointers and objects are done through the parameters.
// (When in C++, use & parameters for return, but we're not there yet)
//
// 'void' return functions are only used for functions that are syntactically
// unable to fail.
//

//
// ev2citrusleaf_object calls
// 

// fill out the object structure with the string in question - no allocs
void ev2citrusleaf_object_init(ev2citrusleaf_object *o);
void ev2citrusleaf_object_set_null(ev2citrusleaf_object *o);
void ev2citrusleaf_object_init_str(ev2citrusleaf_object *o, char *str);
void ev2citrusleaf_object_init_str2(ev2citrusleaf_object *o, char *str, size_t buf_len);
void ev2citrusleaf_object_dup_str(ev2citrusleaf_object *o, char *str);
void ev2citrusleaf_object_init_blob(ev2citrusleaf_object *o, void *buf, size_t buf_len);
void ev2citrusleaf_object_init_blob2(enum ev2citrusleaf_type btype,ev2citrusleaf_object *o, void *buf, size_t buf_len);
void ev2citrusleaf_object_dup_blob(ev2citrusleaf_object *o, void *buf, size_t buf_len);
void ev2citrusleaf_object_dup_blob2(enum ev2citrusleaf_type btype, ev2citrusleaf_object *o, void *buf, size_t buf_len);
void ev2citrusleaf_object_init_int(ev2citrusleaf_object *o, int64_t i);
void ev2citrusleaf_object_free(ev2citrusleaf_object *o); 
void ev2citrusleaf_bins_free(ev2citrusleaf_bin *bins, int n_bins);


// Callback to report results of database operations.
//
// If bins array is present, application is responsible for freeing bins'
// objects using ev2citrusleaf_bins_free(), but client will free bins array.
//
// expiration is reported as seconds from now, the time the callback is made.
// (Currently the server returns an epoch-based time which the client converts
// to seconds from now. So if the server's and client's real time clocks are out
// of sync, the reported expiration will be inaccurate. We plan to have the
// server do the conversion, eventually.)

typedef void (*ev2citrusleaf_callback) (int return_value,  ev2citrusleaf_bin *bins, int n_bins,
		uint32_t generation, uint32_t expiration, void *udata );


// Caller may replace client library's mutex calls with these callbacks (e.g. to
// include them in an application monitoring scheme). To use this feature, pass
// a valid ev2citrusleaf_lock_callbacks pointer in ev2citrusleaf_init(). To let
// the client library do its own mutex calls, pass null in ev2citrusleaf_init().
//
// As defined in cf_base/include/citrusleaf/cf_hooks.h:
//
typedef struct cf_mutex_hooks_s {
	// Allocate and initialize new lock.
	void *(*alloc)(void);
	// Release all storage held in 'lock'.
	void (*free)(void *lock);
	// Acquire an already-allocated lock at 'lock'.
	int (*lock)(void *lock);
	// Release a lock at 'lock'.
	int (*unlock)(void *lock);
} cf_mutex_hooks;

typedef cf_mutex_hooks ev2citrusleaf_lock_callbacks;


typedef struct ev2citrusleaf_cluster_static_options_s {
	// true		- A transaction may specify that its callback be made in a
	//			  different thread from that of the transaction call.
	// false	- Default - A transaction always specifies that its callback be
	//			  made in the same thread as that of the transaction call.
	bool	cross_threaded;
} ev2citrusleaf_cluster_static_options;
/**
  Initialize the asynchronous Citrusleaf library
*/
int ev2citrusleaf_init(ev2citrusleaf_lock_callbacks *lock_cb);

void ev2citrusleaf_shutdown(bool fail_requests);

//
// This call will print stats to stderr
//
void ev2citrusleaf_print_stats(void);


/**
 * Create a cluster object - all requests are made on a cluster
 */
//was:
//struct ev2citrusleaf_cluster_s;

struct cf_ll_element_s;
typedef struct cf_ll_element_s {
	struct cf_ll_element_s *next;
	struct cf_ll_element_s *prev;
} cf_ll_element;
typedef volatile uint32_t cf_atomic32;

typedef struct threadsafe_runtime_options_s {
	cf_atomic32				socket_pool_max;

	cf_atomic32				read_master_only;

	cf_atomic32				throttle_reads;
	cf_atomic32				throttle_writes;

	// These change together under the lock.
	uint32_t				throttle_threshold_failure_pct;
	uint32_t				throttle_window_seconds;
	uint32_t				throttle_factor;

	// For groups of options that need to change together:
	void*					lock;
} threadsafe_runtime_options;

//questionable:
typedef unsigned long pthread_t;


typedef struct cf_vector_s {
	uint32_t value_len;
	unsigned int flags;
	unsigned int alloc_len; // number of elements currently allocated
	unsigned int len;       // number of elements in table, largest element set
	uint8_t *vector;
	bool	stack_struct;
	bool	stack_vector;
	void    *LOCK;
} cf_vector;


struct ev2citrusleaf_cluster_s {
	// Global linked list of all clusters.
	cf_ll_element			ll_e;

	// Sanity-checking field.
	uint32_t				MAGIC;

	// Seems this flag isn't used, but is set from public API. TODO - deprecate?
	bool					follow;

	// Used only with internal cluster management option.
	pthread_t				mgr_thread;
	bool					internal_mgr;

	// Cluster management event base, specified by app or internally created.
	struct event_base*		base;

	// Associated cluster management DNS event base.
	struct evdns_base*		dns_base;

	// Cluster-specific functionality options.
	ev2citrusleaf_cluster_static_options	static_options;
	threadsafe_runtime_options				runtime_options;

	// List of host-strings and ports added by the user.
	cf_vector				host_str_v;		// vector is pointer-type
	cf_vector				host_port_v;	// vector is integer-type
};






typedef struct ev2citrusleaf_cluster_s ev2citrusleaf_cluster;


typedef struct ev2citrusleaf_cluster_runtime_options_s {
	// Per node, the maximum number of open sockets that will be pooled for
	// re-use. Default value is 300. (Note that this does not limit how many
	// sockets can be open at once, just how many are kept for re-use.)
	uint32_t	socket_pool_max;

	// true		- Force all get transactions to read only the master copy.
	// false	- Default - Allow get transactions to read master or replica.
	bool		read_master_only;

	// If transactions to a particular database server node are failing too
	// often, the client can be set to "throttle" transactions to that node by
	// specifying which transactions may be throttled, the threshold failure
	// percentage above which to throttle, and how hard to throttle. Throttling
	// is done by purposefully dropping a certain percentage of transactions
	// (API calls return EV2CITRUSLEAF_FAIL_THROTTLED for dropped transactions)
	// in order to lighten the load on the node.
	//
	// f: actual failure percentage, measured over several seconds
	// t: percentage of transactions to drop
	// t = (f - throttle_threshold_failure_pct) * throttle_factor
	// ... where t is capped at 90%.

	// true		- Allow reads to be throttled.
	// false	- Default - Don't throttle reads.
	bool		throttle_reads;

	// true		- Allow writes to be throttled.
	// false	- Default - Don't throttle writes.
	bool		throttle_writes;

	// Throttle when actual failure percentage exceeds this. Default value is 2.
	uint32_t	throttle_threshold_failure_pct;

	// Measure failure percentage over this interval. Default 15, min 1, max 65.
	uint32_t	throttle_window_seconds;

	// How hard to throttle. Default value is 10.
	uint32_t	throttle_factor;
} ev2citrusleaf_cluster_runtime_options;

// Client uses base for internal cluster management events. If NULL is passed,
// an event base and thread are created internally for cluster management.
//
// If NULL opts is passed, ev2citrusleaf_cluster_static_options defaults are
// used. The opts fields are copied and opts only needs to last for the scope of
// this call.
ev2citrusleaf_cluster *ev2citrusleaf_cluster_create(struct event_base *base,
		const ev2citrusleaf_cluster_static_options *opts);

// Before calling ev2citrusleaf_cluster_destroy(), stop initiating transaction
// requests to this cluster, and make sure that all in-progress transactions are
// completed, i.e. their callbacks have been made.
//
// If a base was passed in ev2citrusleaf_cluster_create(), the app must:
// - First, exit the base's event loop.
// - Next, call ev2citrusleaf_cluster_destroy().
// - Finally, free the base.
// During ev2citrusleaf_cluster_destroy() the client will re-run the base's
// event loop to handle all outstanding internal cluster management events.
void ev2citrusleaf_cluster_destroy(ev2citrusleaf_cluster *asc);

// Get the current cluster runtime options. This will return the default options
// if ev2citrusleaf_cluster_set_options() has never been called. It's for
// convenience - get the current/default values in opts, modify the desired
// field(s), then pass opts in ev2citrusleaf_cluster_set_options().
int ev2citrusleaf_cluster_get_runtime_options(ev2citrusleaf_cluster *asc,
		ev2citrusleaf_cluster_runtime_options *opts);

// Set/change cluster runtime options. The opts fields are copied and opts only
// needs to last for the scope of this call.
int ev2citrusleaf_cluster_set_runtime_options(ev2citrusleaf_cluster *asc,
		const ev2citrusleaf_cluster_runtime_options *opts);

// Adding a host to the cluster list which will always be checked for membership
// As this entire interface is async, the number of hosts in the cluster must be
// checked with a different, non-blocking, call
int ev2citrusleaf_cluster_add_host(ev2citrusleaf_cluster *cl, char *host, short port);

// Following is the act of tracking the cluster members as there are changes in
// ownership of the cluster, and load balancing. Following is enabled by default,
// turn it off only for debugging purposes
void ev2citrusleaf_cluster_follow(ev2citrusleaf_cluster *cl, bool flag);

// Gets the number of active nodes
// -1 means the call failed - the cluster object is invalid
// 0 means no nodes - won't get fast response
// more is good!
//
// Warning!  A typical code pattern would be to create the cluster, add a host,
// and loop on this call. That will never succeed, because libevent doesn't
// have an active thread. You will need to give libevent a thread, which is shown
// in the example distributed with this client. Or don't use threads and just
// dispatch.
int ev2citrusleaf_cluster_get_active_node_count(ev2citrusleaf_cluster *cl);

// Returns the number of requests in progress.
// May use this to check that all requests on a cluster are cleared before
// calling ev2citrusleaf_cluster_destroy().
int ev2citrusleaf_cluster_requests_in_progress(ev2citrusleaf_cluster *cl);

// For troubleshooting only - force all nodes in the cluster to refresh their
// partition table information.
void ev2citrusleaf_cluster_refresh_partition_tables(ev2citrusleaf_cluster *cl);


//
// An extended information structure
// when you want to control every little bit of write information you can
//
// Expiration is in *seconds from now*.
//
typedef struct {
	bool	use_generation;
	uint32_t generation;
	uint32_t expiration;
	ev2citrusleaf_write_policy wpol;
} ev2citrusleaf_write_parameters;

//
// Get and put calls
//

int 
ev2citrusleaf_get_all(ev2citrusleaf_cluster *cl, char *ns, char *set, ev2citrusleaf_object *key, 
	int timeout_ms, ev2citrusleaf_callback cb, void *udata, struct event_base *base);

int
ev2citrusleaf_get_all_digest(ev2citrusleaf_cluster *cl, char *ns, cf_digest *d, int timeout_ms, 
	ev2citrusleaf_callback cb, void *udata, struct event_base *base);

int 
ev2citrusleaf_put(ev2citrusleaf_cluster *cl, char *ns, char *set, ev2citrusleaf_object *key,
	ev2citrusleaf_bin *bins, int n_bins, ev2citrusleaf_write_parameters *wparam, 
	int timeout_ms, ev2citrusleaf_callback cb, void *udata, struct event_base *base);

int 
ev2citrusleaf_put_digest(ev2citrusleaf_cluster *cl, char *ns, cf_digest *d,
	ev2citrusleaf_bin *bins, int n_bins, ev2citrusleaf_write_parameters *wparam, 
	int timeout_ms, ev2citrusleaf_callback cb, void *udata, struct event_base *base);

int 
ev2citrusleaf_get(ev2citrusleaf_cluster *cl, char *ns, char *set, ev2citrusleaf_object *key,
	const char **bins, int n_bins, int timeout_ms, ev2citrusleaf_callback cb, void *udata,
	struct event_base *base);

int 
ev2citrusleaf_get_digest(ev2citrusleaf_cluster *cl, char *ns, cf_digest *d,
	const char **bins, int n_bins, int timeout_ms, ev2citrusleaf_callback cb, void *udata,
	struct event_base *base);

int 
ev2citrusleaf_delete(ev2citrusleaf_cluster *cl, char *ns, char *set, ev2citrusleaf_object *key,
	ev2citrusleaf_write_parameters *wparam, int timeout_ms, ev2citrusleaf_callback cb, void *udata,
	struct event_base *base);

int 
ev2citrusleaf_delete_digest(ev2citrusleaf_cluster *cl, char *ns, cf_digest *d,
	ev2citrusleaf_write_parameters *wparam, int timeout_ms, ev2citrusleaf_callback cb, void *udata,
	struct event_base *base);

int
ev2citrusleaf_operate(ev2citrusleaf_cluster *cl, char *ns, char *set, ev2citrusleaf_object *key,
	ev2citrusleaf_operation *ops, int n_ops, ev2citrusleaf_write_parameters *wparam, 
	int timeout_ms, ev2citrusleaf_callback cb, void *udata, struct event_base *base);

// This call actually doesn't exist
// int
// ev2citrusleaf_operate_digest(ev2citrusleaf_cluster *cl, char *ns, cf_digest *d,
// 	ev2citrusleaf_operation *ops, int n_ops, ev2citrusleaf_write_parameters *wparam, 
// 	int timeout_ms, ev2citrusleaf_callback cb, void *udata, struct event_base *base);

//
// Batch calls
//

// An array of these is returned via ev2citrusleaf_get_many_cb.
//
// result will be either EV2CITRUSLEAF_OK or EV2CITRUSLEAF_FAIL_NOTFOUND.
//
// For the result of a ev2citrusleaf_exists_many_digest() call, bins and n_bins
// will always be NULL and 0 respectively.
//
// For the result of a ev2citrusleaf_get_many_digest() call, if result is
// EV2CITRUSLEAF_OK bin data will be present. Application is responsible for
// freeing bins' objects using ev2citrusleaf_bins_free(), but client will free
// bins array.

typedef struct ev2citrusleaf_rec_s {
	int					result;			// result for this record
	cf_digest			digest;			// digest identifying record
	uint32_t			generation;		// record generation
	uint32_t			expiration;		// record expiration, seconds from now
	ev2citrusleaf_bin	*bins;			// record data - array of bins
	int					n_bins;			// number of bins in bins array
} ev2citrusleaf_rec;

// Batch-get callback, to report results of ev2citrusleaf_get_many_digest() and
// ev2citrusleaf_exists_many_digest() calls.
//
// result is "overall" result - may be OK while individual record results are
// EV2CITRUSLEAF_FAIL_NOTFOUND. Typically not OK when batch job times out or one
// or more nodes' transactions fail. In all failure cases partial record results
// may be returned, therefore n_recs may be less than n_digests requested.
//
// recs is the array of individual record results. Client will free recs array.
// n_recs is the number of records in recs array.
//
// The order of records in recs array does not necessarily correspond to the
// order of digests in request.

typedef void (*ev2citrusleaf_get_many_cb) (int result, ev2citrusleaf_rec *recs, int n_recs, void *udata);

// Get a batch of records, specified by array of digests.
//
// Pass NULL bins, 0 n_bins, to get all bins. (Note - bin name filter not yet
// supported by server - pass NULL, 0.)
//
// If return value is EV2CITRUSLEAF_OK, the callback will always be made. If
// not, the callback will not be made.

int
ev2citrusleaf_get_many_digest(ev2citrusleaf_cluster *cl, const char *ns, const cf_digest *digests, int n_digests,
		const char **bins, int n_bins, int timeout_ms, ev2citrusleaf_get_many_cb cb, void *udata, struct event_base *base);

// Check existence of a batch of records, specified by array of digests.
//
// If return value is EV2CITRUSLEAF_OK, the callback will always be made. If
// not, the callback will not be made.

int
ev2citrusleaf_exists_many_digest(ev2citrusleaf_cluster *cl, const char *ns, const cf_digest *digests, int n_digests,
		int timeout_ms, ev2citrusleaf_get_many_cb cb, void *udata, struct event_base *base);


//
// the info interface allows
// information about specific cluster features to be retrieved on a host by host basis
// size_t is in number of bytes. String is null terminated as well
// API CONTRACT: *callee* frees the 'response' buffer
typedef void (*ev2citrusleaf_info_callback) (int return_value, char *response, size_t response_len, void *udata);

int ev2citrusleaf_info(
	struct event_base *base, struct evdns_base *dns_base,
	char *host, short port, char *names, int timeout_ms,
	ev2citrusleaf_info_callback cb, void *udata);

//
// This debugging call can be useful for tracking down errors and coordinating with server failures
//
int
ev2citrusleaf_calculate_digest(const char *set, const ev2citrusleaf_object *key, cf_digest *digest);

//
// Logging - see cf_log.h
//